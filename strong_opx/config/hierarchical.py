from functools import cached_property
from typing import Any, Collection

from strong_opx.config.base import Config
from strong_opx.exceptions import ImproperlyConfiguredError

empty = object()


class HierarchicalConfig:
    missing_required_config_template = (
        "strong-opx is improperly configured. Configure {section}.{option} using\n\n"
        "  $ strong-opx config {section}.{option} <{placeholder}>"
    )

    def __init__(self, configs: Collection[Config]):
        self.configs = configs

    def get(self, section: str, option: str, fallback=None) -> Any:
        for config in self.configs:
            value = config.get(section, option, fallback=empty)
            if value is not empty:
                return value

        return fallback

    def get_required(self, section: str, option: str, placeholder="value") -> Any:
        value = self.get(section, option, fallback=empty)
        if value is empty:
            raise ImproperlyConfiguredError(
                self.missing_required_config_template.format(option=option, section=section, placeholder=placeholder)
            )

        return value

    @cached_property
    def ssh_user(self) -> str:
        return self.get_required("ssh", "user", placeholder="remote-login-user")

    @cached_property
    def ssh_key(self) -> str:
        return self.get_required("ssh", "key", placeholder="path-to-ssh-key")

    @cached_property
    def git_ssh_key(self) -> str:
        return self.get("git", "ssh.key", fallback=self.ssh_key)

    @cached_property
    def terraform_executable(self) -> str:
        return self.get("terraform", "executable", fallback="terraform")

    @cached_property
    def packer_executable(self) -> str:
        return self.get("packer", "executable", fallback="packer")

    @cached_property
    def ansible_playbook_executable(self) -> str:
        return self.get("ansible", "playbook.executable", fallback="ansible-playbook")

    @cached_property
    def docker_executable(self) -> str:
        return self.get("docker", "executable", fallback="docker")

    @cached_property
    def kubectl_executable(self) -> str:
        return self.get("kubectl", "executable", fallback="kubectl")
