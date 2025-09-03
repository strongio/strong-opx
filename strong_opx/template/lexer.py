import functools
import re
from typing import List, NamedTuple, Optional, Tuple, Union

RE_RAW_START = re.compile(r"\{%\s*raw\s*%}")
RE_RAW_END = re.compile(r"\{%\s*endraw\s*%}")

RE_COMMENT_START = re.compile(r"\{#")
RE_COMMENT_END = re.compile(r"#}")

RE_VARIABLE_START = re.compile(r"\{\{")
RE_VARIABLE_END = re.compile(r"}}")

RE_BLOCK_START = re.compile(r"\{%")
RE_BLOCK_END = re.compile(r"%}")

RE_LEGACY_VARIABLE_START = re.compile(r"\${{?")
RE_LEGACY_VARIABLE_END = re.compile(r"}?}")


class LexerError(Exception):
    def __init__(self, message: str, start_pos: int, end_pos: Optional[int] = None):
        self.message = message
        self.start_pos = start_pos
        self.end_pos = end_pos


class Token(NamedTuple):
    value: str
    position: int

    @property
    def end_position(self) -> int:
        return self.position + len(self.value)


class TemplateLexer:
    def __init__(self, value: str):
        self.template = value
        self._tokens = []

    def tokenize(self) -> List[Union[Token, Tuple[Token, Token, Token]]]:
        self._tokens = []
        length = len(self.template)
        position = 0

        pattern_handlers = (
            # Check for {% raw %} first
            (RE_RAW_START, self._handle_raw_block),
            (RE_COMMENT_START, self._skip_comment),  # Check for comments
            (RE_VARIABLE_START, functools.partial(self._handle_tag, RE_VARIABLE_END)),
            (RE_BLOCK_START, functools.partial(self._handle_tag, RE_BLOCK_END)),
            (
                RE_LEGACY_VARIABLE_START,
                functools.partial(self._handle_tag, RE_LEGACY_VARIABLE_END, strip_whitespaces=False),
            ),
        )

        while position < length:
            text_start = position
            next_delim_pos = length

            next_delim_match = None
            next_delim_handler = None

            for pattern, handler in pattern_handlers:
                match = pattern.search(self.template, position)
                if match and match.start() < next_delim_pos:
                    next_delim_pos = match.start()

                    next_delim_match = match
                    next_delim_handler = handler

            if next_delim_pos > text_start:
                text = self.template[text_start:next_delim_pos]
                self._tokens.append(Token(text, text_start))

            if next_delim_handler:
                position = next_delim_handler(next_delim_match.end(), next_delim_match)
            else:
                position = next_delim_pos

        return self._tokens

    def _skip_comment(self, content_start: int, start_match: re.Match) -> int:
        end_match = RE_COMMENT_END.search(self.template, content_start)
        if end_match:
            return end_match.end()

        raise LexerError("Unclosed tag", start_match.start(), start_match.end())

    def _handle_raw_block(self, content_start: int, start_match: re.Match) -> int:
        end_match = RE_RAW_END.search(self.template, content_start)
        if end_match is None:
            raise LexerError("Unclosed tag", start_match.start(), start_match.end())

        content_end = end_match.start()
        if content_end > content_start:
            content = self.template[content_start:content_end]
            self._tokens.append(
                (
                    Token("{% raw %}", start_match.start()),
                    Token(content, content_start),
                    Token("{% endraw %}", end_match.start()),
                )
            )

        return end_match.end()

    def _handle_tag(self, end_re: re.Pattern, content_start: int, start_match: re.Match, strip_whitespaces=True) -> int:
        end_match = end_re.search(self.template, content_start)
        if end_match is None:
            raise LexerError("Unclosed tag", start_match.start(), start_match.end())

        content_end = end_match.start()
        if content_end > content_start:
            content = self.template[content_start:content_end]

            if strip_whitespaces:
                actual_length = len(content)
                content = content.lstrip()
                content_start += actual_length - len(content)

                content = content.rstrip()

            self._tokens.append(
                (
                    Token(start_match.group(0), start_match.start()),
                    Token(content, content_start),
                    Token(end_match.group(0), end_match.start()),
                )
            )

        return end_match.end()
