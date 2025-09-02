import os
from contextlib import contextmanager
from typing import Any, TextIO

import yaml

from strong_opx.exceptions import YAMLError
from strong_opx.utils.tracking import OpxFloat, OpxInteger, OpxString, Position, set_position_from_yaml_mark
from strong_opx.vault import VaultCipher
from strong_opx.yaml.cython_compat import construct_yaml_map, construct_yaml_seq


@contextmanager
def _yaml_loader(file_path: str):
    with open(file_path, "r") as f:
        loader = OpxYAMLLoader(stream=f, file_path=file_path)
        try:
            yield loader
        except yaml.YAMLError as ex:
            kwargs = {}

            if isinstance(ex, yaml.MarkedYAMLError):
                lines = [ex.problem]
                kwargs["start_pos"] = Position.from_yaml_mark(ex.problem_mark)
            else:
                lines = str(ex).splitlines()

            raise YAMLError(
                "\n".join(lines),
                file_path=file_path,
                hint="error maybe elsewhere in the file depending on the exact syntax problem",
                **kwargs,
            )
        finally:
            loader.dispose()


def load(file_path: str) -> Any:
    with _yaml_loader(file_path) as loader:
        return loader.get_single_data()


def load_all(file_path: str) -> list[Any]:
    documents = []
    with _yaml_loader(file_path) as loader:
        while loader.check_data():
            documents.append(loader.get_data())

    return documents


class OpxYAMLLoader(yaml.SafeLoader):
    def __init__(self, stream: TextIO, file_path: str):
        self.file_path = file_path
        super().__init__(stream)

    def include(self, node: yaml.ScalarNode):
        rel_path = self.construct_scalar(node)
        abs_path = os.path.join(os.path.dirname(self.file_path), rel_path)
        if not os.path.exists(abs_path):
            raise YAMLError(
                f"Included file ({rel_path}) not found at {abs_path}",
                file_path=self.file_path,
                start_pos=Position.from_yaml_mark(node.start_mark),
                end_pos=Position.from_yaml_mark(node.end_mark),
            )

        return load(abs_path)

    def vault(self, node):
        value = VaultCipher.parse(self.construct_scalar(node))
        set_position_from_yaml_mark(value, node.start_mark, node.end_mark)
        return value

    def construct_yaml_int(self, node: yaml.ScalarNode):
        value = OpxInteger(super().construct_yaml_int(node))
        set_position_from_yaml_mark(value, node.start_mark, node.end_mark)
        return value

    def construct_yaml_float(self, node: yaml.ScalarNode):
        value = OpxFloat(super().construct_yaml_float(node))
        set_position_from_yaml_mark(value, node.start_mark, node.end_mark)
        return value

    def construct_yaml_timestamp(self, node: yaml.ScalarNode):
        value = super().construct_yaml_timestamp(node)
        set_position_from_yaml_mark(value, node.start_mark, node.end_mark)
        return value

    def construct_yaml_str(self, node: yaml.ScalarNode):
        value = OpxString(self.construct_scalar(node))
        set_position_from_yaml_mark(value, node.start_mark, node.end_mark)
        return value


# YAML Tags
OpxYAMLLoader.add_constructor("tag:yaml.org,2002:int", OpxYAMLLoader.construct_yaml_int)
OpxYAMLLoader.add_constructor("tag:yaml.org,2002:float", OpxYAMLLoader.construct_yaml_float)
OpxYAMLLoader.add_constructor("tag:yaml.org,2002:timestamp", OpxYAMLLoader.construct_yaml_timestamp)
OpxYAMLLoader.add_constructor("tag:yaml.org,2002:str", OpxYAMLLoader.construct_yaml_str)
OpxYAMLLoader.add_constructor("tag:yaml.org,2002:seq", construct_yaml_seq)
OpxYAMLLoader.add_constructor("tag:yaml.org,2002:map", construct_yaml_map)

# Additional Tags
OpxYAMLLoader.add_constructor("!include", OpxYAMLLoader.include)
OpxYAMLLoader.add_constructor("!vault", OpxYAMLLoader.vault)
