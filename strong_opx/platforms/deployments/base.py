import logging
import os
import tempfile
from typing import TYPE_CHECKING

from strong_opx.exceptions import CommandError
from strong_opx.template import FileTemplate

if TYPE_CHECKING:
    from strong_opx.platforms import Platform
    from strong_opx.project import Environment, Project

logger = logging.getLogger(__name__)


class NodeConfig(str):
    def __new__(cls, name: str, path: str):
        instance = super().__new__(cls, name)
        instance.path = path
        return instance


class DeploymentProvider:
    name: str
    platform: "Platform"

    def __init__(self, project: "Project", environment: "Environment", platform: "Platform"):
        self.project = project
        self.environment = environment
        self.platform = platform

    def select_nodes(self, nodes: list[str]) -> list[str]:
        prefix = f"{self.name}/"
        return [node for node in nodes if node.startswith(prefix)]

    def deploy_node(self, node: str) -> bool:
        raise NotImplementedError()


class ConfigDeploymentProvider(DeploymentProvider):
    allowed_extensions: tuple[str, ...] = None

    def select_nodes(self, nodes: list[str]) -> list[NodeConfig]:
        provide_nodes = []
        for node in nodes:
            if node.startswith(f"{self.name}/"):
                node_path = os.path.join(self.project.path, node)
            elif node.startswith(f"{self.name}:"):
                _, node_path = node.split(":", 1)
            else:
                continue

            if not os.path.exists(node_path):
                raise CommandError(f"Unable to locate {node} at {node_path}")

            provide_nodes.append(NodeConfig(node, node_path))

        return provide_nodes

    def is_config_applicable(self, file_name: str) -> bool:
        file_name, extension = os.path.splitext(file_name)
        if self.allowed_extensions and extension not in self.allowed_extensions:
            return False

        environment = os.path.splitext(file_name)[1]
        return not environment or environment.replace(".", "") == self.environment.name

    def deploy_node(self, node: NodeConfig) -> bool:
        if os.path.isdir(node.path):
            config_files = [
                os.path.join(node.path, file_name)
                for file_name in os.listdir(node.path)
                if self.is_config_applicable(file_name=file_name)
            ]
        else:
            config_files = [node.path]

        if not config_files:  # Empty directory or no config for this environment
            logger.warning("No config file found for current environment. Deployment skipped")
            return False

        with tempfile.TemporaryDirectory(prefix=os.path.basename(node.path)) as td:
            for source_path in config_files:
                target_path = os.path.join(td, os.path.basename(source_path))
                FileTemplate(source_path).render_to_file(target_path, self.environment.context)

            return self.deploy(node, td)

    def deploy(self, node: NodeConfig, directory: str) -> bool:
        raise NotImplementedError()
