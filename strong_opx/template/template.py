import ast
import re
import sys
import traceback
from typing import TYPE_CHECKING, Any, Callable, Optional

from strong_opx.exceptions import CommandError, ConfigurationError, TemplateError, UndefinedVariableError, VariableError
from strong_opx.template.compiler import CONTEXT_VAR_NAME, OUTPUT_VAR_NAME, TemplateCompiler
from strong_opx.template.registry import TEMPLATE_FILTERS
from strong_opx.template.variable import VariableStore
from strong_opx.utils.tracking import Position, get_position

if TYPE_CHECKING:
    from strong_opx.template import Context

TOKEN_RE = re.compile(r"(?s)({{.*?}}|{%.*?%}|{#.*?#}|\${?{[^}]+}}?)")


class Template:
    module: ast.Module
    variables: VariableStore

    def __init__(self, value: str):
        self.value = value
        self.file_path = get_position(value)[0]

        self.compile()

    def render(self, context: "Context") -> str:
        filename = self.file_path or "<template>"
        local_context: dict[str, Any] = {
            "lines": [],
            CONTEXT_VAR_NAME: context,
        }

        try:
            exec(
                compile(self.module, filename, "exec"),
                self.variables.globals,
                local_context,
            )
        except Exception as e:
            handled_e = self.handle_exception(filename, e)
            if handled_e is None:
                raise

            raise handled_e from e

        if OUTPUT_VAR_NAME in local_context:
            return local_context[OUTPUT_VAR_NAME]

        return "".join(local_context["lines"])

    def handle_exception(self, filename: str, e: Exception) -> Optional[CommandError]:
        """
        Handle an exception raised during template rendering. If the exception is a known template error, it is
        handled and returned. Otherwise, a generic TemplateError is returned.

        :param filename: The filename of the template
        :param e: The exception raised
        :return: The handled exception or None if the exception is not a template error
        """

        for frame, _ in traceback.walk_tb(sys.exc_info()[-1]):
            if frame.f_code.co_filename == filename:
                break
        else:
            return None

        if isinstance(e, VariableError):
            e.errors[0].file_path = self.file_path

            ref = self.variables.get_ref(e.var_name)
            if ref is not None:
                e.errors[0].start_pos = ref.start_pos
                e.errors[0].end_pos = ref.end_pos

                return e

        if isinstance(e, UndefinedVariableError):
            for i, name in enumerate(e.names):
                e.errors[i].file_path = self.file_path

                ref = self.variables.get_ref(name)
                if ref is not None:
                    e.errors[i].start_pos = ref.start_pos
                    e.errors[i].end_pos = ref.end_pos

            return e

        if isinstance(e, ConfigurationError):
            for error in e.errors:
                error.file_path = self.file_path
                error.start_pos = Position(line=frame.f_lineno, column=None)

            return e

        try:
            from strong_opx.providers import current_provider_error_handler

            current_provider_error_handler(e)
        except CommandError as ex:
            return ex
        except Exception as ex:
            e = ex  # Fall back to generic error handling

        return TemplateError(
            f"({e.__class__.__name__}) {e}",
            file_name=get_position(self.value)[0],
            start_pos=Position(line=frame.f_lineno, column=None),
        )

    def compile(self):
        offset = 0
        ops_stack = []

        tokens = [t for t in TOKEN_RE.split(self.value) if t]

        # If there are multiple tokens, render as string otherwise keep the original datatype
        compiler = TemplateCompiler(self.value, as_string=len(tokens) > 1)
        inside_raw_block = 0

        for token in tokens:
            if inside_raw_block:
                action_tag = None
                if token.startswith("{%"):
                    action_tag = compiler.str_strip(token[2:-2], offset + 2)[0]

                if action_tag == "raw":
                    inside_raw_block += 1
                elif action_tag == "endraw":
                    inside_raw_block -= 1

                if inside_raw_block:
                    compiler.compile_constant(token, offset)

            elif token.startswith("{#"):  # Comment: ignore it and move on.
                pass

            elif token.startswith("{{"):  # An expression to evaluate.
                compiler.compile_expression(token, offset)

            elif token.startswith("${"):  # $-style expression.
                compiler.compile_legacy_expression(token, offset)

            elif token.startswith("{%"):  # Action tag: split into words and parse further.
                action_tag, start_offset, end_offset = compiler.str_strip(token[2:-2], offset + 2)
                action_tag, tag_args = compiler.split_on_whitespace(action_tag)

                if action_tag == "if":  # An if statement: evaluate the expression to determine if.
                    ops_stack.append("if")
                    compiler.compile_if(tag_args, start_offset + 2)
                elif action_tag == "for":  # A loop: iterate over expression result.
                    ops_stack.append("for")
                    compiler.compile_for(tag_args, start_offset)
                elif action_tag == "raw":
                    if tag_args:
                        compiler.syntax_error("raw action tag does not take any argument", offset, offset + len(token))

                    inside_raw_block += 1
                elif action_tag.startswith("end"):  # End-something. Pop the ops stack.
                    if tag_args:
                        compiler.syntax_error("End block does not take any argument", offset, offset + len(token))

                    end_what = action_tag[3:]
                    if not ops_stack:
                        compiler.syntax_error("Unexpected end block", offset, offset + len(token))

                    start_what = ops_stack.pop()
                    if start_what != end_what:
                        compiler.syntax_error(
                            f"Expecting end{start_what} block, got end{end_what}", offset, offset + len(token)
                        )

                    compiler.close_block()
                elif action_tag == "else":
                    if tag_args:
                        compiler.syntax_error("else block does not take any argument", offset, offset + len(token))

                    if not ops_stack or ops_stack[-1] != "if":
                        compiler.syntax_error("Unexpected else block", offset, offset + len(token))

                    compiler.start_else_block(start_offset, end_offset)
                else:
                    compiler.syntax_error(f"Unknown action tag: {action_tag}", start_offset, end_offset)

            else:  # Literal content
                compiler.compile_constant(token, offset)

            offset += len(token)

        if ops_stack:
            compiler.syntax_error("Unclosed tags: {}".format(", ".join(ops_stack)), offset, offset + 1)

        self.module = compiler.finalize()
        self.variables = compiler.variables

    @classmethod
    def register_filter(cls, name: str, func: Callable = None):
        if name in TEMPLATE_FILTERS:
            raise ValueError(f"Filter {name} is already exists")

        def register(f: Callable):
            TEMPLATE_FILTERS[name] = f
            return f

        if func is None:
            return register

        return register(func)
