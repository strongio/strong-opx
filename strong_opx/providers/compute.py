import re
from dataclasses import field
from ipaddress import IPv4Address
from typing import Optional, Union

from pydantic.dataclasses import dataclass
from pydantic_core import CoreSchema, core_schema

from strong_opx.compat import StrEnum
from strong_opx.providers.discovery import current_provider, current_provider_class
from strong_opx.utils.mapping import CaseInsensitiveMultiTagDict


def filter_instances_by_environment_tag_if_exists(
    instances: list["ComputeInstanceDescription"],
) -> list["ComputeInstanceDescription"]:
    """
    Given instances, return all instances which:
    * Do NOT have an "environment" tag (case-insensitive)
    OR
    * DO have an "environment" tag (case-insensitive) AND the value of that tag matches the current
      environment (also case-insensitive)

    This function is intentionally "permissive" with the instances that it does NOT filter out. In particular:
    * Allow instances without an "Environment" tag. Do not assume an instance is not part of the current
      environment, if the instance does not have an "Environment" tag.
    * Allow instances with multiple "Environment" tags, if at least one value matches the current environment. It's
      possible multiple environments use the same instance.

    This "permissiveness" is expected to be more backwards compatible than being more restrictive.
    """

    from strong_opx.project import Project

    selected_environment = Project.current().selected_environment
    this_environment = selected_environment.name.lower()

    def keep_instance(instance: "ComputeInstanceDescription") -> bool:
        environment_tags = instance.tags.get("environment")
        return not environment_tags or any(tag.lower() == this_environment for tag in environment_tags)

    return [instance for instance in instances if keep_instance(instance)]


class ComputeInstance:
    hostname: str

    def __init__(self, value: Union[str, IPv4Address]):
        self.hostname = value
        self._ip_address = None
        self._instance_id = None

        if isinstance(value, IPv4Address):
            self._ip_address = value
        else:
            self._instance_id = value

    @property
    def ip_address(self) -> IPv4Address:
        if self._ip_address is None:
            self._ip_address = self._instance_ip_address()

        return self._ip_address

    @property
    def instance_id(self) -> str:
        if self._instance_id is None:
            self._instance_id = self._instance_id_from_ip_address()

        return self._instance_id

    @property
    def current_state(self) -> "ComputeInstanceState":
        return self.describe().state

    def describe(self):
        if self._instance_id is not None:
            return self._describe_by_instance_id()

        return self._describe_by_ip()

    def _describe_by_ip(self) -> "ComputeInstanceDescription":
        instances = current_provider().query_compute_instances(self.ip_address)

        if self._ip_address.is_private:
            instances = filter_instances_by_environment_tag_if_exists(instances)

        if len(instances) == 1:
            return instances[0]

        public_or_private = "private" if self._ip_address.is_private else "public"

        if len(instances) == 0:
            raise ValueError(f'Unable to find an instance with {public_or_private} IP "{self._ip_address}"')

        raise ValueError(
            f'Expected to find exactly one instance with {public_or_private} IP "{self._ip_address}", but found '
            f"{len(instances)}. "
            f'Instance IDs: {", ".join(instance.instance_id for instance in instances)}.'
        )

    def _describe_by_instance_id(self) -> "ComputeInstanceDescription":
        return current_provider().describe_compute_instance(self.instance_id)

    def _instance_ip_address(self) -> IPv4Address:
        instance = self._describe_by_instance_id()
        if instance.public_ip:
            return IPv4Address(instance)

        return instance.private_ip

    def _instance_id_from_ip_address(self) -> str:
        return self._describe_by_ip().instance_id

    def __str__(self):
        if self._ip_address is not None and self._instance_id is None:
            return str(self._ip_address)

        if self._instance_id is not None and self._ip_address is None:
            return self._instance_id

        return f"{self._ip_address} ({self._instance_id})"

    def __repr__(self):
        return f"<{type(self).__name__}: {self.hostname}>"

    def __eq__(self, other):
        if not isinstance(other, ComputeInstance):
            return False

        return self.hostname == other.hostname

    def __hash__(self):
        return hash(self.hostname)

    @classmethod
    def parse(cls, value: Union[str, IPv4Address]) -> "ComputeInstance":
        if isinstance(value, IPv4Address):
            return cls(value)
        elif not isinstance(value, str):
            raise TypeError(f"Expected str or IPv4Address, got {type(value).__name__}")

        try:
            return cls(IPv4Address(value))
        except ValueError as ex:
            # If it's not a valid IPv4 address, it might be an instance ID
            provider_class = current_provider_class()
            if provider_class.compute_instance_id_re is None:
                raise ex  # If the provider does not support instance IDs, raise the original ValueError

            if not re.match(provider_class.compute_instance_id_re, value):
                raise ValueError(
                    f"Invalid instance ID format: {value}. Expected format: {provider_class.compute_instance_id_re}"
                )

        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler) -> CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls.parse, ref="ComputeInstance", serialization=core_schema.to_string_ser_schema()
        )


class ComputeInstanceState(StrEnum):
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass
class ComputeInstanceDescription:
    instance_id: str
    state: ComputeInstanceState

    private_ip: IPv4Address
    public_ip: Optional[IPv4Address] = None
    tags: CaseInsensitiveMultiTagDict[str, str] = field(default_factory=CaseInsensitiveMultiTagDict)
