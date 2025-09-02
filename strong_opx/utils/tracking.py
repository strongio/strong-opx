from dataclasses import dataclass
from typing import Any, Optional

import yaml


@dataclass(frozen=True)
class Position:
    """
    Represents a position in a file. Both line and column are 1-based.
    """

    line: int
    column: Optional[int]

    def __iter__(self):
        yield self.line
        yield self.column

    def __gt__(self, other):
        if self.line > other.line:
            return True
        if self.line == other.line:
            return (self.column or 0) > (other.column or 0)
        return False

    def __lt__(self, other):
        if self.line < other.line:
            return True
        if self.line == other.line:
            return (self.column or 0) < (other.column or 0)
        return False

    def __ge__(self, other):
        return self > other or self == other

    def __le__(self, other):
        return self < other or self == other

    @classmethod
    def from_yaml_mark(cls, mark: yaml.Mark) -> "Position":
        # YAML line & column are 0-based, but we want 1-based
        return cls(line=mark.line + 1, column=mark.column + 1)

    @classmethod
    def from_offset(cls, value: str, offset: int, initial_line: int = 1, initial_col: int = 1) -> "Position":
        """
        Return the line number and column number of a character, where it resides in source value.

        :remarks: initial_line and initial_col is useful when the value is a substring of a larger value,
            and the initial line/col offset is the line/col offset of the substring in the larger value.

        :param value: source value
        :param offset: 0-based index in template
        :param initial_line: Optionally specify the initial line offset. Initial line offset is the line offset of
            the substring in the larger value.
        :param initial_col: Optionally specify the initial column offset. Initial column offset is the column offset
            of the substring in the larger value.
        :return: Position(1-based index of line, 1-based index in that line)
        """
        line = value.count("\n", 0, offset)
        col_offset = offset - value.rfind("\n", 0, offset)

        if not line:
            col_offset += initial_col - 1

        return cls(line + initial_line, col_offset)


class OpxObjectBase:
    _file_path: str = None
    _start_pos: Position = None
    _end_pos: Position = None


class OpxString(OpxObjectBase, str):
    pass


class OpxInteger(OpxObjectBase, int):
    pass


class OpxFloat(OpxObjectBase, float):
    pass


class OpxMapping(OpxObjectBase, dict):
    def __getattr__(self, item):
        try:
            return super().__getitem__(item)
        except AttributeError:
            return self[item]


class OpxSequence(OpxObjectBase, list):
    pass


def set_position(value: Any, file_path: str, start_pos: Optional[Position], end_pos: Optional[Position]) -> None:
    value._file_path = file_path
    value._start_pos = start_pos
    value._end_pos = end_pos


def set_position_from_yaml_mark(value: Any, start_mark: yaml.Mark, end_mark: yaml.Mark) -> None:
    value._file_path = start_mark.name
    value._start_pos = Position.from_yaml_mark(start_mark)
    value._end_pos = Position.from_yaml_mark(end_mark)


def get_position(value: Any) -> tuple[Optional[str], Optional[Position], Optional[Position]]:
    return getattr(value, "_file_path", None), getattr(value, "_start_pos", None), getattr(value, "_end_pos", None)
