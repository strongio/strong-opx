import ast
import os
import sys
import traceback
from typing import TYPE_CHECKING, Any, Callable, Optional

from strong_opx.exceptions import CommandError, ConfigurationError, TemplateError, UndefinedVariableError, VariableError
from strong_opx.template.compiler import CONTEXT_VAR_NAME, INCLUDE_VAR_NAME, OUTPUT_VAR_NAME, TemplateCompiler
from strong_opx.template.lexer import LexerError, TemplateLexer, Token
from strong_opx.template.registry import TEMPLATE_FILTERS
from strong_opx.template.variable import VariableStore
from strong_opx.utils.tracking import Position, get_position

if TYPE_CHECKING:
    from strong_opx.template import Context


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
            INCLUDE_VAR_NAME: self.include,
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
        try:
            tokens = TemplateLexer(self.value).tokenize()
        except LexerError as e:
            raise TemplateCompiler(self.value).syntax_error(e.message, e.start_pos, e.end_pos)

        # If there are multiple tokens, render as string otherwise keep the original datatype
        compiler = TemplateCompiler(self.value, as_string=len(tokens) > 1)
        ops_stack = []

        for token in tokens:
            if isinstance(token, Token):
                compiler.compile_constant(token.value, token.position)
            else:
                start, content, end = token

                if start.value == "{{":  # An expression to evaluate.
                    compiler.compile_expression(content.value, content.position)

                elif start.value.startswith("${"):  # $-style expression.
                    expr = start.value + content.value + end.value
                    compiler.compile_legacy_expression(expr, start.position)

                elif start.value == "{%":  # Action tag: split into words and parse further.
                    action_tag, tag_args = compiler.split_on_whitespace(content.value)

                    if action_tag == "if":  # An if statement: evaluate the expression to determine if.
                        ops_stack.append(("if", content.position, content.position + 2))
                        compiler.compile_if(tag_args, content.position)
                    elif action_tag == "for":  # A loop: iterate over expression result.
                        ops_stack.append(("for", content.position, content.position + 3))
                        compiler.compile_for(tag_args, content.position)
                    elif action_tag == "raw":
                        # When no-args are given, that scenario is handled separately
                        if tag_args:
                            raise compiler.syntax_error(
                                "raw action tag does not take any argument", content.position, content.end_position
                            )
                    elif action_tag == "include":
                        compiler.compile_include(tag_args, start.position, content.position, content.end_position)

                    elif action_tag.startswith("end"):  # End-something. Pop the ops stack.
                        if tag_args:
                            raise compiler.syntax_error(
                                "End block does not take any argument", content.position, content.end_position
                            )

                        end_what = action_tag[3:]
                        if not ops_stack:
                            raise compiler.syntax_error("Unexpected end block", start.position, start.end_position)

                        start_what = ops_stack.pop()[0]
                        if start_what != end_what:
                            raise compiler.syntax_error(
                                f"Expecting end{start_what} block, got end{end_what}",
                                start.position,
                                start.end_position,
                            )

                        compiler.close_block()
                    elif action_tag == "else":
                        if tag_args:
                            raise compiler.syntax_error(
                                "else block does not take any argument", content.position, content.end_position
                            )

                        if not ops_stack or ops_stack[-1][0] != "if":
                            raise compiler.syntax_error("Unexpected else block", content.position, content.end_position)

                        compiler.start_else_block(content.position, content.end_position)
                    else:
                        raise compiler.syntax_error(
                            f"Unknown action tag: {action_tag}", content.position, content.end_position
                        )

                elif start.value == "{% raw %}":
                    compiler.compile_constant(content.value, content.position)

                else:
                    raise RuntimeError(f"Internal error: unknown token type: {start.value} at {start.position}")

        if ops_stack:
            value, start_pos, end_pos = ops_stack.pop()
            raise compiler.syntax_error(f"Unclosed tag: {value}", start_pos, end_pos)

        self.module = compiler.finalize()
        self.variables = compiler.variables

    def include(self, template_name: str, *, context: "Context", indent=0) -> str:
        template_dir = "."
        if self.file_path:
            template_dir = os.path.dirname(self.file_path)

        template_path = os.path.join(template_dir, template_name)
        if not os.path.isfile(template_path):
            raise FileNotFoundError(f"Included template '{template_name}' not found in '{template_dir}'")

        with open(template_path, "r") as f:
            content = f.read()

        rendered_content = Template(content).render(context)
        if indent > 0:
            rendered_content = rendered_content.replace("\n", "\n" + (" " * indent))

        return rendered_content

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
