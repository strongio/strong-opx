import os.path
import tempfile
from unittest import TestCase

from parameterized import parameterized

from strong_opx.exceptions import ConfigurationError
from strong_opx.utils.tracking import OpxFloat, OpxInteger, OpxMapping, OpxObjectBase, OpxSequence, OpxString, Position
from strong_opx.yaml import load


class OpxYAMLLoaderTest(TestCase):
    def assertIsMarked(self, value):
        self.assertIsInstance(getattr(value, "_start_pos"), Position)
        self.assertIsInstance(getattr(value, "_end_pos"), Position)

    @parameterized.expand(
        [
            (b"key: string value", OpxString("string value")),
            (b"key: 1", OpxInteger(1)),
            (b"key: 1.5", OpxFloat(1.5)),
            (b"key: [1, 2]", OpxSequence([1, 2])),
            (b"key: {1: 2}", OpxMapping({1: 2})),
        ]
    )
    def test_load(self, content: bytes, expected_value):
        with tempfile.NamedTemporaryFile() as f:
            f.write(content)
            f.flush()

            loaded_yaml = load(f.name)

        self.assertEqual(expected_value, loaded_yaml["key"])
        self.assertIsInstance(loaded_yaml["key"], OpxObjectBase)

    def test_include(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "f1.yml"), "w") as f:
                f.write(f"key1: !include f2.yml")

            with open(os.path.join(td, "f2.yml"), "w") as f:
                f.write("key2: value2")

            loaded_yaml = load(os.path.join(td, "f1.yml"))

        self.assertDictEqual({"key1": {"key2": "value2"}}, loaded_yaml)

    def test_include__unknown_file(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(b"!include hello.yml")
            f.flush()

            with self.assertRaises(ConfigurationError) as cm:
                load(f.name)

        self.assertIsInstance(cm.exception, ConfigurationError)
