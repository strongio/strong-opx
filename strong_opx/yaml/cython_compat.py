"""
Cython generator doesn't work with PyYAML's custom constructors.
This module isn't Cythonized and only holds the custom constructors for loading list and dict
"""

import yaml

from strong_opx.utils.tracking import OpxMapping, OpxSequence, set_position_from_yaml_mark


def construct_yaml_seq(loader: yaml.SafeLoader, node: yaml.SequenceNode):
    value = OpxSequence()
    set_position_from_yaml_mark(value, node.start_mark, node.end_mark)
    yield value
    value.extend(loader.construct_sequence(node))


def construct_yaml_map(loader: yaml.SafeLoader, node: yaml.MappingNode):
    value = OpxMapping()
    set_position_from_yaml_mark(value, node.start_mark, node.end_mark)
    yield value
    value.update(loader.construct_mapping(node))
