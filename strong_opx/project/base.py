import logging
import os
from functools import cached_property
from typing import Optional

from strong_opx.config import PROJECT_CONFIG_FILE, opx_config, system_config
from strong_opx.config.hierarchical import HierarchicalConfig
from strong_opx.exceptions import ImproperlyConfiguredError, ProcessError, ProjectEnvironmentError, ProjectError
from strong_opx.helm import HelmConfig
from strong_opx.project.config import ProjectConfig
from strong_opx.project.environment import Environment, load_environment
from strong_opx.project.vars import VariableConfig
from strong_opx.providers import Provider
from strong_opx.providers.secret_provider import SecretProvider
from strong_opx.utils.shell import shell

logger = logging.getLogger(__name__)


class Project:
    selected_environment: Optional["Environment"] = None

    def __init__(
        self,
        name: str,
        path: str,
        provider: Provider,
        secret_provider: SecretProvider,
        vars_config: VariableConfig,
        helm_config: HelmConfig,
    ):
        self.provider = provider
        self.name = name
        self.path = path
        self.helm_config = helm_config

        self.secret_provider = secret_provider
        self.vars_config = vars_config
        self.config = HierarchicalConfig([system_config.get_project_config(self.name), system_config])
        self.environments_dir = os.path.join(self.path, "environments")

    def __new__(cls, *args, **kwargs):
        instance = getattr(cls, "_instance", None)
        if instance is None:
            instance = super().__new__(cls)
            setattr(cls, "_instance", instance)

        return instance

    @classmethod
    def current(cls) -> Optional["Project"]:
        return getattr(cls, "_instance", None)

    @cached_property
    def environments(self) -> list[str]:
        if not os.path.exists(self.environments_dir):
            return []

        return [
            filename
            for filename in os.listdir(self.environments_dir)
            if os.path.isdir(os.path.join(self.environments_dir, filename))
        ]

    def select_environment(self, name: str) -> Environment:
        if name not in self.environments:
            raise ProjectEnvironmentError(f"Unknown environment: {name}")

        self.selected_environment = load_environment(environment_name=name, project=self)
        return self.selected_environment

    def git_revision_hash(self) -> Optional[str]:
        try:
            return (
                shell(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    cwd=self.path,
                )
                .stdout.decode("utf8")
                .strip()
            )
        except ProcessError:
            pass

    def init(self) -> None:
        self.provider.init_project(self)

    @classmethod
    def from_name(cls, project_name: str) -> "Project":
        project_path = system_config.get_project_path(project_name)
        config_path = os.path.join(project_path, PROJECT_CONFIG_FILE)

        if not os.path.exists(config_path) or not os.path.isfile(config_path):
            raise ProjectError(f"{project_name} is not a valid strong-opx project")

        project = cls.from_config(config_path)
        if project.name != project_name:
            raise ImproperlyConfiguredError(
                "Project name specified in config does not match the locally registered name"
            )

        return project

    @classmethod
    def from_config(cls, config_path: str) -> "Project":
        config = ProjectConfig.from_file(config_path)
        if config.strong_opx:
            opx_config.update(config.strong_opx)

        project_path = os.path.dirname(config_path)
        if config.dirname:
            project_path = os.path.join(project_path, config.dirname)

        return Project(
            name=config.name,
            path=project_path,
            secret_provider=config.secret,
            vars_config=config.vars,
            helm_config=config.helm,
            provider=config.provider,
        )
