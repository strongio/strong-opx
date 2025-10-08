import logging
import os
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Any, Callable, TypeVar

from pydantic import Field, ValidationError, create_model

from strong_opx import yaml
from strong_opx.exceptions import ProjectEnvironmentError
from strong_opx.platforms import ALL_PLATFORMS, TPlatform
from strong_opx.project.context_hooks import EnvironHook, ProjectContextHook
from strong_opx.providers import current_docker_registry
from strong_opx.template import Context
from strong_opx.utils.validation import translate_pydantic_errors

if TYPE_CHECKING:
    from strong_opx.platforms.deployments import DeploymentProvider
    from strong_opx.project import Project

T = TypeVar("T")
logger = logging.getLogger(__name__)


class Environment:
    def __init__(self, name: str, project: "Project", vars_: dict[str, str]):
        self.name = name
        self.vars = vars_

        self.project = project
        self.platforms: list[TPlatform] = []
        self.path = os.path.join(project.environments_dir, self.name)
        self.base_context = self.create_context()

    def register_platform(self, platform: TPlatform):
        self.platforms.append(platform)
        platform.init_context(self.base_context)

    def select_platform(self, platform_cls: type[TPlatform]) -> TPlatform:
        for platform in self.platforms:
            if isinstance(platform, platform_cls):
                return platform

        raise ProjectEnvironmentError(f"Environment {self.name} does not support {platform_cls.__name__}")

    def get_context_hooks(self) -> tuple[Callable[["Context"], None], ...]:
        return (
            ProjectContextHook(self.project),
            EnvironHook("STRONG_OPX_"),
            *self.project.provider.get_additional_context_hooks(),
        )

    def create_context(self) -> Context:
        context = Context(
            {
                "ENVIRONMENT": self.name,
                "DOCKER_REGISTRY": current_docker_registry(self),
            }
        )

        for hook in self.get_context_hooks():
            hook(context)

        return context

    @cached_property
    def vault_secret(self):
        return self.project.secret_provider.get_secret(self)

    @cached_property
    def context(self) -> Context:
        context = self.base_context.chain()
        context.update(self.vars)

        var_paths = self.project.vars_config.get_paths(self)
        for file_path in var_paths:
            abs_path = os.path.join(self.project.path, file_path)
            if os.path.exists(abs_path):
                logger.debug(f"Loading vars from {file_path}")
                context.load_from_file(abs_path)
            else:
                logger.warning(f"Unable to locate {file_path}")

        return context

    def init(self):
        self.project.provider.init_environment(self)

    def deploy(self, nodes: list[str]) -> None:
        nodes_by_provider = {}
        for platform in self.platforms:
            for provider_class in platform.deployment_providers:
                provider: "DeploymentProvider" = provider_class(
                    project=self.project, environment=self, platform=platform
                )
                selected_nodes = provider.select_nodes(nodes)
                if selected_nodes:
                    nodes_by_provider[provider] = selected_nodes

        if not nodes_by_provider:
            logger.error("Nothing to deploy")

        for provider, nodes in nodes_by_provider.items():
            for node in nodes:
                logger.info(f"Deploying {node} using {provider.name}")
                provider.deploy_node(node)


def load_environment(environment_name: str, project: "Project") -> Environment:
    config_path = os.path.join(project.environments_dir, environment_name, "config.yml")
    if not os.path.exists(config_path) or not os.path.isfile(config_path):
        raise ProjectEnvironmentError(f"{environment_name} is not a valid strong-opx environment")

    config = yaml.load(config_path)

    environment_config_cls = create_model(
        "EnvironmentConfig",
        vars=(dict[str, Any], Field(default_factory=dict)),
        additional_provider_config=Annotated[dict[str, Any], Field(alias=project.provider.name, default_factory=dict)],
    )

    try:
        validated_config = environment_config_cls(**config)
    except ValidationError as ex:
        raise translate_pydantic_errors(config, ex)

    project.provider.update_config(validated_config.additional_provider_config)
    environment = Environment(name=environment_name, project=project, vars_=validated_config.vars)

    for platform_cls in ALL_PLATFORMS:
        platform = platform_cls.from_config(project=project, environment=environment, **config)
        if platform is not None:
            environment.register_platform(platform)

    return environment
