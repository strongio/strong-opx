from typing import Annotated

from packaging.specifiers import SpecifierSet
from pydantic.dataclasses import dataclass
from pydantic.functional_validators import PlainValidator
from pydantic_core import CoreSchema, core_schema

from strong_opx import __version__ as strong_opx_version
from strong_opx.exceptions import ImproperlyConfiguredError

DEFAULT_TEMPLATING_ENGINE = "strong_opx"


def validate_template_engine(value: str) -> str:
    if value not in ("strong_opx", "jinja2"):
        raise ValueError(f'Unknown templating engine: "{value}". Allowed values: strong_opx, jinja2')

    return value


@dataclass
class StrongOpxConfig:
    templating_engine: Annotated[str, PlainValidator(validate_template_engine)] = DEFAULT_TEMPLATING_ENGINE
    required_version: Annotated[SpecifierSet, PlainValidator(SpecifierSet)] = None

    def update(self, config: "StrongOpxConfig") -> None:
        self.templating_engine = config.templating_engine
        self.required_version = config.required_version

        if self.required_version and not self.required_version.contains(strong_opx_version):
            raise ImproperlyConfiguredError(
                f"Project requires strong-opx{self.required_version} "
                f"but strong-opx=={strong_opx_version} is installed"
            )

    # TODO: Remove that as we remove Cython
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler) -> CoreSchema:
        templating_engine_schema = core_schema.with_default_schema(
            core_schema.chain_schema(
                [
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(validate_template_engine),
                ]
            ),
            default=DEFAULT_TEMPLATING_ENGINE,
        )

        required_version_schema = core_schema.with_default_schema(
            core_schema.chain_schema(
                [
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(SpecifierSet),
                ]
            ),
            default=None,
        )

        return core_schema.dataclass_schema(
            cls,
            core_schema.dataclass_args_schema(
                cls.__name__,
                [
                    core_schema.dataclass_field(
                        "templating_engine",
                        templating_engine_schema,
                        kw_only=True,
                    ),
                    core_schema.dataclass_field(
                        "required_version",
                        required_version_schema,
                        kw_only=True,
                    ),
                ],
            ),
            ["templating_engine", "required_version"],
        )
