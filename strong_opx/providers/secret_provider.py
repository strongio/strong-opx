import logging
import random
import string
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from pydantic_core import CoreSchema, core_schema

from strong_opx.providers.discovery import current_provider_name
from strong_opx.utils.module_loading import import_module_attr_if_exists

if TYPE_CHECKING:
    from strong_opx.project import Environment

logger = logging.getLogger(__name__)


class SecretProvider:
    secret_length: int

    def generate_secret(self):
        return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(self.secret_length))

    def get_secret(self, environment: "Environment") -> str:
        raise NotImplementedError("Current Provider does not implement secret management")

    @classmethod
    def validate_provider_name(cls, value: str) -> str:
        allowed_secret_providers = tuple(current_secret_providers())

        if value not in allowed_secret_providers:
            raise ValueError(
                f'Unknown secret provider: "{value}". Available provider(s): {", ".join(allowed_secret_providers)}'
            )

        return value

    @classmethod
    def validate_provider_class(cls, d: dict[str, Any]):
        d = d.copy()
        provider = d.pop("provider")
        return current_secret_providers()[provider](**d)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler) -> CoreSchema:
        """
        If the source_type is "SecretProvider", return a schema with the following assertions:
        * The input is a dict, with at least a "provider" key (additional keys are allowed and preserved)
        * The dict is validated by the "validate_provider_class" class method
        * The "provider" key is a string
        * The "provider" value is validated by the "validate_provider_name" class method

        Otherwise, return the result of the handler function.

        Pydantic docs for __get_pydantic_core_schema__():
        https://docs.pydantic.dev/latest/concepts/types/#customizing-validation-with-__get_pydantic_core_schema__

        Param and return comments copied from the Pydantic source code:
        https://github.com/pydantic/pydantic/blob/c067c1b9d0e5ffdf5b0fd53bf0e138cb5924f750/pydantic/main.py#L557-L569

        @param source_type: The class we are generating a schema for. This will generally be the same as the `cls`
                            argument.
        @param handler: Call into Pydantic's internal JSON schema generation. A callable that calls into Pydantic's
                        internal CoreSchema generation logic.
        @return: A `pydantic-core` `CoreSchema`.
        """
        if source_type == SecretProvider:
            # We can't use Literal here because that doesn't work well with OpxString
            provider_schema = core_schema.chain_schema(
                [
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate_provider_name),
                ]
            )

            return core_schema.chain_schema(
                [
                    core_schema.typed_dict_schema(
                        {
                            "provider": core_schema.typed_dict_field(provider_schema, required=True),
                        },
                        extra_behavior="allow",
                    ),
                    core_schema.no_info_plain_validator_function(cls.validate_provider_class),
                ]
            )

        return handler(source_type)


@lru_cache
def current_secret_providers() -> dict[str, SecretProvider]:
    secret_providers = import_module_attr_if_exists(
        f"strong_opx.providers.{current_provider_name()}.secret_provider",
        "SECRET_PROVIDERS",
    )

    return secret_providers or {}
