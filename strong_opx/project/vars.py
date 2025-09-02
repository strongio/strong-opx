from typing import TYPE_CHECKING, Union

from pydantic_core import core_schema

from strong_opx.template import ObjectTemplate

if TYPE_CHECKING:
    from strong_opx.project import Environment

T_VARIABLE_CONFIG = Union[
    str,
    list[Union[str, dict[str, Union[str, list[str]]]]],
    dict[str, Union[str, list[str]]],
]


class VariableConfig:
    value: T_VARIABLE_CONFIG

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value})"

    def get_paths(self, environment: "Environment") -> list[str]:
        if isinstance(self.value, str):
            paths = [self.value]
        elif isinstance(self.value, dict):
            paths = self.value.get(environment.name) or []
            if isinstance(paths, str):
                paths = [paths]
        else:
            paths = []
            for path_config in self.value:
                if isinstance(path_config, dict):
                    path_config = path_config.get(environment.name) or []

                if isinstance(path_config, str):
                    paths.append(path_config)
                else:
                    paths.extend(path_config)

        return ObjectTemplate(environment.base_context).render(paths)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.chain_schema(
            [
                handler(T_VARIABLE_CONFIG),
                core_schema.no_info_plain_validator_function(source_type),
            ]
        )
