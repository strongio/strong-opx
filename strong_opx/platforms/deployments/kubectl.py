import os
import subprocess
import sys
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

import tabulate
from colorama import Style

from strong_opx import yaml
from strong_opx.exceptions import YAMLError
from strong_opx.platforms.deployments.base import ConfigDeploymentProvider, NodeConfig

if TYPE_CHECKING:
    from strong_opx.platforms import KubernetesPlatform


@dataclass
class DeploymentStatus:
    resource_type: str
    resource_name: str
    status: str

    __slots__ = ("resource_type", "resource_name", "status")

    @classmethod
    def from_kubectl_output(cls, output) -> "DeploymentStatus":
        resource, status = output.split(" ")
        type_, name = resource.split("/")
        return cls(
            resource_type=type_.split(".")[0].lower(),
            resource_name=name,
            status=status,
        )


class DeploymentSummary:
    def __init__(self):
        self.lines: list[DeploymentStatus] = []

    def print(self):
        print(
            tabulate.tabulate(
                [(line.resource_type, line.resource_name, line.status) for line in self.lines],
                headers=["Resource", "Name", "Status"],
            )
        )

    @cached_property
    def unchanged_deployments(self) -> list[str]:
        return [
            line.resource_name
            for line in self.lines
            if line.resource_type == "deployment" and line.status == "unchanged"
        ]

    @classmethod
    def parse(cls, kubectl_output: str) -> "DeploymentSummary":
        summary = cls()
        summary.lines = [DeploymentStatus.from_kubectl_output(line) for line in kubectl_output.splitlines()]

        return summary


def preprocess_config_file(node: NodeConfig, manifest_directory: str, manifest_file: str) -> list[dict]:
    full_path = os.path.join(manifest_directory, manifest_file)

    try:
        documents = list(yaml.load_all(full_path))
    except YAMLError as e:
        if not sys.stdin.isatty():
            raise

        print(
            "\nThere is an error while loading rendered Kubernetes manifest. Actual Kubernetes manifest is:\n",
            f"  {Style.BRIGHT}{os.path.join(node.path, manifest_file)}{Style.RESET_ALL}",
        )
        print(str(e), file=sys.stderr)

        print(
            f"\nA temporary file has been created for you to view the rendered manifest:\n"
            f"  {Style.BRIGHT}{full_path}{Style.RESET_ALL}\n",
            file=sys.stderr,
        )

        print(
            "Any changes made to temporary file will be lost. Make changes to the original file instead.",
            file=sys.stderr,
        )
        input("Press Enter when you are done viewing the file to continue...")
        sys.exit(255)

    return documents


class KubeCtlDeploymentProvider(ConfigDeploymentProvider):
    name = "kubectl"
    allowed_extensions = (".yml", ".yaml")
    platform: "KubernetesPlatform"
    rollout_status_supported_kinds = ("deployment", "statefulset")

    def deploy(self, node: NodeConfig, manifest_directory: str) -> None:
        rollout_supported_kinds = []

        for manifest_file in os.listdir(manifest_directory):
            documents = preprocess_config_file(node, manifest_directory, manifest_file)

            for document in documents:
                kind = document.get("kind", "").lower()

                if kind in self.rollout_status_supported_kinds:
                    metadata = document.get("metadata") or {}
                    name = metadata.get("name")
                    namespace = metadata.get("namespace", "default")

                    rollout_supported_kinds.append((kind, name, namespace))

        result = self.platform.kubectl("apply", "-f", manifest_directory, stdout=subprocess.PIPE)
        summary = DeploymentSummary.parse(result.stdout.decode("utf8"))
        summary.print()

        for kind, name, namespace in rollout_supported_kinds:
            self.platform.kubectl("rollout", "status", kind, name, "-n", namespace)

        for kind, name, namespace in rollout_supported_kinds:
            if name in summary.unchanged_deployments:
                # Restart deployment as it was not updated
                self.platform.kubectl("rollout", "restart", "deployment", name, "-n", namespace)
                self.platform.kubectl("rollout", "status", "deployment", name, "-n", namespace)
