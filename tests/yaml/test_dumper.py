import tempfile
from unittest import TestCase

from parameterized import parameterized

from strong_opx.utils.tracking import OpxFloat, OpxInteger, OpxMapping, OpxSequence, OpxString, Position
from strong_opx.yaml import dump


class OpxYAMLDumperTest(TestCase):
    def assertIsMarked(self, value):
        self.assertIsInstance(getattr(value, "_start_pos"), Position)
        self.assertIsInstance(getattr(value, "_end_pos"), Position)

    @parameterized.expand(
        [
            (OpxString("string value"), b"key: string value\n"),
            (OpxInteger(1), b"key: 1\n"),
            (OpxFloat(1.5), b"key: 1.5\n"),
            (
                OpxSequence([1, 2]),
                b"key:\n- 1\n- 2\n",
            ),
            (OpxMapping({1: 2}), b"key:\n  1: 2\n"),
        ]
    )
    def test_dump(self, obj, expected_content: bytes):
        with tempfile.NamedTemporaryFile() as f:
            dump({"key": obj}, f.name)

            content = f.read()

        self.assertEqual(content, expected_content)
