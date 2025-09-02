from dataclasses import asdict
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Any, Callable, Collection, get_type_hints

from pydantic.dataclasses import is_pydantic_dataclass
from pydantic_core import CoreSchema, core_schema

from strong_opx.exceptions import ConfigurationError, ErrorDetail
from strong_opx.providers.compute import ComputeInstanceDescription

if TYPE_CHECKING:
    from strong_opx.project import Environment, Project
    from strong_opx.template import Context


class Provider:
    name: str  # Dynamic attribute set by the provider module
    config = None

    compute_instance_id_re: str = None

    def __init__(self, config=None) -> None:
        self.config = config

    def init_project(self, project: "Project") -> None:
        raise NotImplementedError()

    def init_environment(self, environment: "Environment") -> None:
        raise NotImplementedError()

    def describe_compute_instance(self, instance_id: str) -> ComputeInstanceDescription:
        raise NotImplementedError()

    def query_compute_instances(self, ip_address: IPv4Address) -> list[ComputeInstanceDescription]:
        raise NotImplementedError()

    def start_compute_instance(self, instance_ids: Collection[str], wait: bool = True) -> None:
        raise NotImplementedError()

    def stop_compute_instance(self, instance_ids: Collection[str], wait: bool = True) -> None:
        raise NotImplementedError()

    def assume_service_role(self, role: str):
        raise NotImplementedError()

    def update_kubeconfig(self, cluster_name: str, kubeconfig_path: str) -> None:
        raise NotImplementedError()

    def get_additional_context_hooks(self) -> tuple[Callable[["Context"], None], ...]:
        return ()

    def handle_error(self, ex: Exception) -> None:
        raise ex

    def update_config(self, provider_config: dict[str, Any]) -> None:
        config_cls = get_type_hints(type(self)).get("config")
        if config_cls is None:
            if provider_config:
                raise ConfigurationError(
                    ErrorDetail(
                        f"Provider '{self.name}' does not accept any configuration",
                        hint="Remove the provider configuration from your environment file.",
                    )
                )

            return

        config = config_cls(**provider_config)
        for k, v in asdict(config).items():
            if v is None:
                continue

            setattr(self.config, k, v)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler) -> CoreSchema:
        config_cls = get_type_hints(cls).get("config")
        if config_cls is not None:
            if not is_pydantic_dataclass(config_cls):
                raise TypeError(f"{cls.__name__}.config ({repr(config_cls)}) must be a pydantic dataclass")

            schemas = [handler.generate_schema(config_cls), core_schema.no_info_plain_validator_function(source_type)]
        else:
            schemas = [core_schema.no_info_plain_validator_function(lambda x: cls())]

        return core_schema.chain_schema(schemas)
