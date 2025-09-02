from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel

from strong_opx.exceptions import CommandError
from strong_opx.platforms.deployments import DeploymentProvider
from strong_opx.platforms.plugins import PlatformPlugin

if TYPE_CHECKING:
    from strong_opx.project import Environment, Project
    from strong_opx.template import Context


class Platform:
    config_class: type[BaseModel]
    config_namespace: str = None

    deployment_providers: tuple[type[DeploymentProvider], ...] = ()
    plugins: dict[str, type[PlatformPlugin]] = {}

    def __init__(self, project: "Project", environment: "Environment", **kwargs: Any):
        self.project = project
        self.environment = environment

        for k, v in kwargs.items():
            setattr(self, k, v)

    def init_context(self, context: "Context") -> None:
        pass

    @classmethod
    def extract_relevant_config(cls, config: dict[str, Any]) -> Optional[dict[str, Any]]:
        values = {}

        for name, field in cls.config_class.model_fields.items():
            if name in config:
                values[name] = config[name]
            elif field.is_required():
                return None

        if values:
            return values

        return None

    @classmethod
    def from_config(cls, project: "Project", environment: "Environment", **config: Any) -> Optional["Platform"]:
        if cls.config_namespace is not None:
            platform_config = config.get(cls.config_namespace)
        else:
            platform_config = cls.extract_relevant_config(config)

        if platform_config is not None:
            platform_config = cls.config_class(**platform_config).model_dump()
            return cls(project=project, environment=environment, **platform_config)

    def plugin(self, plugin_name: str) -> "PlatformPlugin":
        plugin_class = self.plugins.get(plugin_name.lower())
        if plugin_class is None:
            raise CommandError(f"Unknown plugin: {plugin_name}")

        return plugin_class(self)
