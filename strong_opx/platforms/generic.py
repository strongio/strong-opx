import itertools
import logging
import os
import tempfile
from contextlib import contextmanager
from typing import TYPE_CHECKING, Annotated, Generator, Optional

from pydantic import AfterValidator, BaseModel, model_validator

from strong_opx import config, yaml
from strong_opx.exceptions import CommandError, ComputeInstanceError
from strong_opx.platforms import Platform
from strong_opx.providers import ComputeInstance
from strong_opx.providers.compute import ComputeInstanceState
from strong_opx.utils.shell import shell

if TYPE_CHECKING:
    from strong_opx.template import Context

logger = logging.getLogger(__name__)
SUPPORTED_SSH_METHODS = ("direct", "bastion", "aws_ssm")


def validate_ssh_method(value: str) -> str:
    if value not in SUPPORTED_SSH_METHODS:
        raise ValueError(f"Unsupported SSH method: {value}")

    return value


class GenericPlatformConfig(BaseModel):
    ssh_method: Annotated[str, AfterValidator(validate_ssh_method)] = None
    hosts: dict[str, list[ComputeInstance]]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.ssh_method is None:
            self.ssh_method = "bastion" if "bastion" in self.hosts else "direct"

    @model_validator(mode="after")
    def check_bastion_config(self) -> "GenericPlatformConfig":
        if self.ssh_method == "bastion" and "bastion" not in self.hosts:
            raise ValueError('SSH method is set to "bastion" but no bastion host is configured')

        if "bastion" in self.hosts and len(self.hosts["bastion"]) > 1:
            raise ValueError("Only one bastion host is allowed")

        for group, group_hosts in self.hosts.items():
            if group == "bastion":
                group_hosts[0].hostname = group
                continue

            for host_index, host in enumerate(group_hosts):
                host.hostname = f"{group}:{host_index}"

        return self


class GenericPlatform(Platform):
    config_class = GenericPlatformConfig

    if TYPE_CHECKING:
        ssh_method: str
        hosts: dict[str, list[ComputeInstance]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for host_groups in self.hosts.values():
            for host in host_groups:
                host.platform = self

    def init_context(self, context: "Context"):
        def read_git_ssh_key():
            with open(self.project.config.git_ssh_key) as f:
                return f.read()

        context["GIT_IDENTITY"] = read_git_ssh_key

    def deploy(self) -> None:
        playbook_path = os.path.join(self.project.path, "playbooks", "deploy.yml")
        if not os.path.exists(playbook_path):
            raise CommandError(f"Missing playbooks/deploy.yml")

        with self.ensure_instances_are_running():
            self.ansible_playbook(playbook_path)

    def ansible_playbook(
        self,
        playbook: str,
        host_groups: list[str] = None,
        additional_args: tuple[str, ...] = None,
    ):
        with self.ansible_host_inventory(host_groups) as inventory, self.ansible_extra_vars() as extras:
            args = (
                self.project.config.ansible_playbook_executable,
                playbook,
                "-i",
                inventory,
                "-u",
                self.project.config.ssh_user,
                "--private-key",
                self.project.config.ssh_key,
                "--extra-vars",
                f"@{extras}",
            )

            os.environ["STRONG_OPX_PROJECT"] = self.project.name
            os.environ["STRONG_OPX_ENVIRONMENT"] = self.environment.name
            os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "False"
            os.environ["ANSIBLE_FILTER_PLUGINS"] = config.ANSIBLE_FILTER_PLUGINS
            os.environ["ANSIBLE_PIPELINING"] = "True"
            os.environ["ANSIBLE_SSH_PIPELINING"] = "True"
            if additional_args:
                args += additional_args

            shell(args, cwd=self.project.path)

    def ssh_proxy_command(self, hostname: str = None) -> Optional[str]:
        if self.ssh_method == "direct":
            return None

        if self.ssh_method == "bastion":
            if hostname == "bastion":
                return None

            bastion = self.hosts["bastion"][0]
            return (
                f"ssh -A -o StrictHostKeyChecking=no -i {self.project.config.ssh_key} "
                f"-W %h:%p {self.project.config.ssh_user}@{bastion.ip_address}"
            )

        return (
            f'sh -c "aws ssm start-session --target %h --document-name '
            f'AWS-StartSSHSession --parameters portNumber=%p"'
        )

    def resolve_instance(self, hostname: str) -> list[ComputeInstance]:
        if hostname == "all":
            return list(itertools.chain.from_iterable(self.hosts.values()))

        if ":" in hostname:
            for instance in itertools.chain.from_iterable(self.hosts.values()):
                if instance.hostname == hostname:
                    return [instance]

            raise ComputeInstanceError(f'Compite Instance "{hostname}" not found')

        if hostname in self.hosts:
            group_hosts = self.hosts[hostname]
            if not group_hosts:
                raise ValueError(f'Host group "{hostname}" has no hosts')

            return group_hosts

        try:
            instance = ComputeInstance.parse(hostname)
        except ValueError:
            raise ComputeInstanceError(f"Unknown host group or invalid format: {hostname}")

        instance.platform = self
        return [instance]

    def get_ssh_host(self, instance: ComputeInstance) -> str:
        if self.ssh_method == "aws_ssm":
            return instance.instance_id

        return str(instance.ip_address)

    @contextmanager
    def ensure_instances_are_running(self, host_groups: list[str] = None):
        stopped_instances = []
        logger.info("Getting instance states...")

        for group, group_hosts in self.hosts.items():
            if host_groups and group not in host_groups:
                continue

            for instance in group_hosts:
                state = instance.current_state

                if state not in (ComputeInstanceState.RUNNING, ComputeInstanceState.STOPPED):
                    raise RuntimeError(f'Host "{instance}" is in invalid state: {state}')

                if state == ComputeInstanceState.STOPPED:
                    stopped_instances.append(instance.instance_id)

        provider = self.project.provider
        if stopped_instances:
            logger.info(f"Starting {len(stopped_instances)} stopped instances...")
            provider.start_compute_instance(stopped_instances, wait=True)

        yield
        if stopped_instances:
            logger.info("Restoring instances states...")
            provider.stop_compute_instance(stopped_instances, wait=False)

    @contextmanager
    def ansible_host_inventory(self, host_groups: list[str]) -> Generator[str, None, None]:
        t = tempfile.NamedTemporaryFile(mode="w+", suffix=".yml")
        stream = t.__enter__()

        host_inventory = {}

        for group, instances in self.hosts.items():
            if host_groups and group not in host_groups:
                continue

            proxy_command = self.ssh_proxy_command(group)
            ansible_ssh_common_args = "-o StrictHostKeyChecking=no -o ConnectTimeout=60"
            if proxy_command:
                ansible_ssh_common_args = f"{ansible_ssh_common_args} -o ProxyCommand='{proxy_command}'"

            host_inventory[group] = {
                "hosts": {
                    self.get_ssh_host(instance): {
                        "ansible_ssh_common_args": ansible_ssh_common_args,
                        "ansible_python_interpreter": "/usr/bin/python3",
                    }
                    for instance in instances
                }
            }

        yaml.dump(host_inventory, stream)
        yield stream.name
        t.__exit__(None, None, None)

    @contextmanager
    def ansible_extra_vars(self) -> Generator[str, None, None]:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yml") as t:
            context = self.environment.context.as_dict()
            yaml.dump(context, t)
            yield t.name
