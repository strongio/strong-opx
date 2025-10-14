import re
from typing import TextIO

from strong_opx.utils.tracking import OpxString, Position, set_position

VARIABLE_NAME_RE = re.compile(r'variable\s+\"([^"]+)\"\s+{')
VARIABLE_DEFAULT_RE = re.compile(r"default\s+=")


class FileReader:
    def __init__(self, file_path: str, stream: TextIO):
        self.file_path = file_path
        self.stream = stream

        self.line = 1
        self.column = 1

    def peak(self, n: int) -> str:
        s = self.stream.read(n)
        self.stream.seek(self.stream.tell() - len(s), 0)
        return s

    def read(self, n: int) -> str:
        s = self.stream.read(n)
        breaks = s.count("\n")
        if breaks:
            self.line += breaks
            self.column = len(s) - s.rindex("\n")
        else:
            self.column += len(s)

        return s

    def discard_whitespaces(self):
        while self.peak(1).isspace():
            self.read(1)

    def discard_comment(self, s) -> bool:
        if s == "#":
            self.discard_single_line_comment()
            return True

        if s == "/":
            n = self.peak(1)

            if n == "/":
                self.discard_single_line_comment()
                return True

            if n == "*":
                self.discard_multi_line_comment()
                return True

        return False

    def discard_single_line_comment(self) -> None:
        while True:
            s = self.read(1)
            if not s or s == "\n":
                break

    def discard_multi_line_comment(self) -> None:
        while True:
            s = self.read(1)
            if not s:
                break

            if s == "*" and self.peak(1) == "/":
                self.read(2)
                break

    def read_string(self, end: str) -> str:
        content = ""
        while True:
            s = self.read(1)
            if not s:
                break

            if s == end and content[-1:] != "\\":
                break

            content += s

        return content

    def read_until(self, end: str) -> str:
        content = ""
        while True:
            s = self.read(1)
            if not s:
                break

            if self.discard_comment(s):
                continue

            content += s
            if s in "'\"":
                content += self.read_string(s) + s

            if s == end:
                break

        return content

    def read_block(self, start: str, end: str) -> str:
        stack = 1
        content = ""
        while True:
            s = self.read(1)
            if not s:
                break

            if self.discard_comment(s):
                content += "\n"
                continue

            content += s
            if s in "'\"":
                content += self.read_string(s) + s
                continue

            if s == start:
                stack += 1
            elif s == end:
                stack -= 1
                if not stack:
                    break

        return content


class HCLVariableExtractor:
    def __init__(self):
        self.required_vars: set[OpxString] = set()
        self.optional_vars: set[OpxString] = set()

    def extract(self, file_path: str, stream: TextIO) -> None:
        reader = FileReader(file_path, stream)

        while True:
            reader.discard_whitespaces()
            initial_line = reader.line
            initial_col = reader.column

            block_prefix = reader.read_until("{")
            if not block_prefix:
                break

            block_content = reader.read_block("{", "}")
            match = VARIABLE_NAME_RE.match(block_prefix)
            if not match:
                continue

            var_name = OpxString(match.group(1))
            start_offset, end_offset = match.span(1)
            set_position(
                var_name,
                file_path,
                Position.from_offset(block_prefix, start_offset, initial_line, initial_col),
                Position.from_offset(block_prefix, end_offset, initial_line, initial_col),
            )

            if VARIABLE_DEFAULT_RE.search(block_content):
                self.optional_vars.add(var_name)
            else:
                self.required_vars.add(var_name)
