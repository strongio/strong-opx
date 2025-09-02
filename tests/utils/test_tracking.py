from dataclasses import dataclass
from unittest import TestCase

from parameterized import parameterized
from yaml import Mark

from strong_opx.utils.tracking import OpxString, Position, get_position, set_position_from_yaml_mark


def test_position_from_mark():
    mark = Mark("", 0, 0, 1, None, 0)

    position = Position.from_yaml_mark(mark)
    assert position.line == 1
    assert position.column == 2


def test_set_position_from_yaml_mark():
    start_mark = Mark("somefile", 0, 0, 1, None, 0)
    end_mark = Mark("somefile", 0, 0, 4, None, 0)

    value = OpxString("hello")
    set_position_from_yaml_mark(value, start_mark, end_mark)
    file_path, start_pos, end_pos = get_position(value)

    assert file_path == "somefile"
    assert start_pos == Position(1, 2)
    assert end_pos == Position(1, 5)


class TestPositionFromOffset(TestCase):
    @parameterized.expand(
        [
            ("hello", 2, Position(1, 3)),
            ("hello\nworld", 0, Position(1, 1)),
            ("hello\nworld", 7, Position(2, 2)),
            ("hello\nworld", 10, Position(2, 5)),
        ]
    )
    def test_position_from_offset(self, value: str, offset: int, expected_outcome):
        outcome = Position.from_offset(value, offset)
        self.assertEqual(outcome, expected_outcome)

    @dataclass
    class ATestCase:
        value: str
        offset: int
        initial_line: int
        initial_col: int
        expected_outcome: Position

    test_cases = [
        # Single-line with different initial positions
        ATestCase(value="hello", offset=2, initial_line=1, initial_col=10, expected_outcome=Position(1, 12)),
        ATestCase(value="hello", offset=2, initial_line=2, initial_col=10, expected_outcome=Position(2, 12)),
        # Multi-line with different offsets & initial positions
        ATestCase(value="hello\nworld", offset=0, initial_line=1, initial_col=10, expected_outcome=Position(1, 10)),
        ATestCase(value="hello\nworld", offset=1, initial_line=2, initial_col=10, expected_outcome=Position(2, 11)),
        ATestCase(value="hello\nworld", offset=7, initial_line=1, initial_col=10, expected_outcome=Position(2, 2)),
        ATestCase(value="hello\nworld", offset=8, initial_line=2, initial_col=10, expected_outcome=Position(3, 3)),
    ]

    @parameterized.expand([(test_case,) for test_case in test_cases])
    def test_position_from_offset__with_initial_position(self, test_case: ATestCase):
        outcome = Position.from_offset(
            value=test_case.value,
            offset=test_case.offset,
            initial_line=test_case.initial_line,
            initial_col=test_case.initial_col,
        )
        self.assertEqual(outcome, test_case.expected_outcome)
