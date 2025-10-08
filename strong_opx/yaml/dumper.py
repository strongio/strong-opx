from typing import Any, TextIO, Union

import yaml
from yaml.representer import SafeRepresenter

from strong_opx.utils.tracking import OpxFloat, OpxInteger, OpxMapping, OpxSequence, OpxString


class OpxYAMLDumper(yaml.Dumper):
    def ignore_aliases(self, data):
        # We don't want to use aliases in YAML, because they're not supported by all tools.
        return True

    def represent_object(self, data):
        return self.represent_str(str(data))


OpxYAMLDumper.add_representer(OpxString, SafeRepresenter.represent_str)
OpxYAMLDumper.add_representer(OpxInteger, SafeRepresenter.represent_int)
OpxYAMLDumper.add_representer(OpxFloat, SafeRepresenter.represent_float)
OpxYAMLDumper.add_representer(OpxSequence, SafeRepresenter.represent_list)
OpxYAMLDumper.add_representer(OpxMapping, SafeRepresenter.represent_dict)
OpxYAMLDumper.add_multi_representer(object, OpxYAMLDumper.represent_object)


def dump_all(data: list[Any], target: Union[str, TextIO]) -> None:
    if isinstance(target, str):
        with open(target, "w") as f:
            return yaml.dump_all(data, f, Dumper=OpxYAMLDumper)
    else:
        return yaml.dump_all(data, target, Dumper=OpxYAMLDumper)


def dump(data: Any, target: Union[str, TextIO]) -> None:
    dump_all([data], target)
