import logging
import os
import signal
from functools import cached_property
from subprocess import CompletedProcess, Popen
from typing import TYPE_CHECKING, Any, Optional

import filelock
from pydantic import BaseModel

from strong_opx import yaml
from strong_opx.config import system_config
from strong_opx.exceptions import CommandError
from strong_opx.platforms.base import Platform
from strong_opx.platforms.deployments import KubeCtlDeploymentProvider
from strong_opx.platforms.plugins import KubernetesDashboardPlugin
from strong_opx.providers import current_docker_registry
from strong_opx.utils.shell import shell
from strong_opx.utils.socket import get_free_tcp_port

if TYPE_CHECKING:
    from strong_opx.template import Context


class KubernetesPlatformConfig(BaseModel):
    cluster_name: str
    service_role: str = None


class KubernetesPlatform(Platform):
    config_class = KubernetesPlatformConfig
    config_namespace = "kubernetes"

    if TYPE_CHECKING:
        cluster_name: str
        service_role: Optional[str]

    deployment_providers = (KubeCtlDeploymentProvider,)
    plugins = {
        "dashboard": KubernetesDashboardPlugin,
    }

    def init_context(self, context: "Context") -> None:
        def images():
            logging.warning("The 'images' context variable is deprecated, use 'DOCKER_REGISTRY' instead.")

            return current_docker_registry(self.environment)

        context["images"] = images

    @cached_property
    def kube_config_path(self) -> str:
        return os.path.join(
            system_config.get_project_config_dir(self.project.name),
            f"kubeconfig-{self.environment.name}",
        )

    def configure_kubernetes(self) -> None:
        provider = self.project.provider

        if self.service_role is not None:
            provider.assume_service_role(self.service_role)

        if not os.path.exists(self.kube_config_path):
            provider.update_kubeconfig(self.cluster_name, self.kube_config_path)
            self._post_process_kubeconfig()

    def kubectl(self, *additional_args: str, **kwargs: Any) -> CompletedProcess:
        self.configure_kubernetes()
        return shell(
            (self.project.config.kubectl_executable, "--kubeconfig", self.kube_config_path) + additional_args,
            **kwargs,
        )

    @cached_property
    def proxy_status_file_path(self) -> str:
        return os.path.join(
            system_config.get_project_config_dir(self.project.name),
            f"kubernetes-proxy-{self.environment.name}",
        )

    def get_proxy_status(self) -> Optional[tuple[int, int]]:
        if not os.path.exists(self.proxy_status_file_path):
            return None

        with open(self.proxy_status_file_path, "r") as f:
            pid = f.readline().strip()
            port = f.readline().strip()

            pid = int(pid) if pid else None
            port = int(port)

        try:
            # `os.kill` will not actually kill the process.
            # (Source: https://stackoverflow.com/a/7647264)
            os.kill(pid, 0)
        except ProcessLookupError:
            os.remove(self.proxy_status_file_path)
        else:
            return pid, port

    def save_proxy_status(self, pid: int, port: int) -> None:
        with open(self.proxy_status_file_path, "w") as f:
            f.write(str(pid))
            f.write("\n")
            f.write(str(port))

    def proxy_lock(self) -> filelock.BaseFileLock:
        return filelock.FileLock(self.proxy_status_file_path + ".lock")

    def start_proxy(self, detached: bool) -> None:
        process = None
        with self.proxy_lock():
            status = self.get_proxy_status()
            if status is not None:
                _, port = status
                print(f"Kubernetes proxy is already running on port {port}")
            else:
                port = get_free_tcp_port()
                print(f"Starting kubernetes proxy on port {port}")

                self.configure_kubernetes()
                process = Popen(
                    (
                        self.project.config.kubectl_executable,
                        "--kubeconfig",
                        self.kube_config_path,
                        "proxy",
                        "-p",
                        str(port),
                    ),
                    start_new_session=True,
                )
                self.save_proxy_status(process.pid, port)

        if process and not detached:
            process.wait()

    def stop_proxy(self) -> bool:
        status = self.get_proxy_status()
        if status:
            pid, _ = status
            if pid is not None:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                return True

        return False

    def ensure_proxy_is_running(self) -> None:
        with self.proxy_lock():
            status = self.get_proxy_status()
            if not status:
                raise CommandError("Kubernetes proxy is not running")

    def _post_process_kubeconfig(self):
        # Remove environment variables, those will be set again automatically by strong-opx when executing
        # kubectl commands.

        kube_config = yaml.load(self.kube_config_path)
        for user in kube_config["users"]:
            user_exec = user["user"]["exec"]
            user_exec.pop("env", None)

        yaml.dump(kube_config, self.kube_config_path)
