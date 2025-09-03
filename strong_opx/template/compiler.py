import ast
import functools
import re
from typing import Union

from strong_opx.exceptions import TemplateError
from strong_opx.template.registry import TEMPLATE_FILTERS
from strong_opx.template.variable import VariableRef, VariableStore
from strong_opx.utils.tracking import Position, get_position

CTX_LOAD = ast.Load()
CTX_STORE = ast.Store()
VAR_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z_0-9]*$")

OUTPUT_VAR_NAME = "_opx_out_"
CONTEXT_VAR_NAME = "_opx_ctx_"
INCLUDE_VAR_NAME = "_opx_include_"


class TemplateCompiler:
    """
    This class parses expressions that are passed to the class and builds a Python Abstract Syntax Tree (AST).

    An instance of the class is generally used like so:
    1. The caller has a collection of tokens it would like to parse
    2. The caller instantiates a TemplateCompiler
    3. For each token, the caller calls one of the TemplateCompiler::compile_*() methods
    4. The caller calls TemplateCompiler::finalize() to halt parsing and retrieve a built AST

    The caller may also make use of TemplateCompiler fields:
    * variables: A `VariableStore` objects that keeps track of all the variables that are defined/accessed in
                 the template.
    * global_vars: A set of variable names whose values are expected to be provided by the caller, when the AST is
                   transformed into code. The TemplateCompiler does NOT generate that code.

    Other fields are:
    * code_modules: code_modules[0] contains all the compiled expressions of self.value. It is what we return to a
                    caller with TemplateCompiler::finalize(). It is also used to keep track of blocks of code.
                    If len(self.code_modules) > 1, the caller is in the middle of parsing a block.
    * selected_body: The body of the currently selected code module. It is usually code_modules[-1].body, but may point
                     to other fields of code_modules[-1], depending on the block(s) being parsed.
    """

    def __init__(self, value: str, as_string: bool = True):
        self.value = value
        self.as_string = as_string

        self.variables = VariableStore()

        self.file_path, initial_pos, _ = get_position(value)
        if initial_pos:
            self.initial_line_no, self.initial_col_offset = initial_pos
        else:
            self.initial_line_no, self.initial_col_offset = 1, 1

        # LRU cache should be local to instance
        self.offset_to_position = functools.lru_cache(maxsize=32)(self.offset_to_position)
        self.code_modules: list[Union[ast.Module, ast.stmt]] = [ast.Module(body=[], type_ignores=[])]
        self.selected_body: list[ast.stmt] = self.code_modules[0].body

        if self.as_string:
            self.append = self.append_as_str

    def offset_to_position(self, offset: int) -> Position:
        """
        Return the line number and column number of a character, where it resides in its source string. It is NOT the
        line/column position of the character in self.value.

        This function treats self.value as an array of characters. The offset parameter is an index to that array.
        This function returns the line number and column number of that index, when splitting self.value into lines,
        with a new line starting at each newline (\n) character.

        The function takes the initial line number and column number into account to calculate the position in the
        source string.

        :param offset: 0-based index in template
        :return: [1-based index of line, 1-based index in that line]
        """
        return Position.from_offset(self.value, offset, self.initial_line_no, self.initial_col_offset)

    def set_location(self, node: ast.AST, start_offset: int, end_offset: int) -> None:
        """
        Given an Abstract Syntax Tree (AST) node with a 'lineno' attribute, update that node's start/end to the
        provided start/end

        :param node: Abstract Syntax Tree node to update
        :param start_offset: Start location to update AST to
        :param end_offset: End location to update AST to
        :return: (none)
        """
        if "lineno" in node._attributes:
            start_pos = self.offset_to_position(start_offset)
            end_pos = self.offset_to_position(end_offset)

            node.lineno = start_pos.line
            node.col_offset = start_pos.column

            node.end_lineno = end_pos.line
            node.end_col_offset = end_pos.column

    @staticmethod
    def str_strip(value: str, offset: int) -> tuple[str, int, int]:
        """
        Strips a string of leading and trailing whitespace, and returns the stripped string, along with the start and
        end offsets which bound the stripped string.

        @param value: The token to strip of whitespace
        @param offset: The offset of the start of the token
        @return: (stripped token, start offset of stripped token, end offset of stripped token)
        """
        t1 = value.lstrip()
        t1_len = len(t1)

        t2 = t1.rstrip()
        t2_len = len(t2)

        start_offset = offset + len(value) - t1_len
        end_offset = start_offset + t2_len

        return t2, start_offset, end_offset

    @staticmethod
    def split_on_whitespace(expr: str) -> tuple[str, str]:
        i = expr.find(" ")
        if i == -1:
            return expr, ""

        return expr[:i], expr[i:]

    def add_statement(self, value: ast.stmt, start_offset: int, end_offset: int) -> None:
        self.set_location(value, start_offset, end_offset)
        self.selected_body.append(value)

    def append(self, value, start_offset: int, end_offset: int) -> None:
        value: ast.Assign = ast.Assign(targets=[ast.Name(id=OUTPUT_VAR_NAME, ctx=CTX_STORE)], value=value)
        self.add_statement(value, start_offset, end_offset)

    def append_as_str(self, value, start_offset: int, end_offset: int) -> None:
        if not isinstance(value, ast.Constant):
            value: ast.Call = ast.Call(ast.Name(id="str", ctx=CTX_LOAD), args=[value], keywords=[])

        n_lines_append = ast.Attribute(value=ast.Name(id="lines", ctx=CTX_LOAD), attr="append", ctx=CTX_LOAD)
        value: ast.Expr = ast.Expr(value=ast.Call(n_lines_append, args=[value], keywords=[]))

        self.add_statement(value, start_offset, end_offset)

    def start_block(self, block: ast.stmt, start_offset: int, end_offset: int):
        """
        Used with ast.stmt subclasses which have "blocks" in Python. For example, 'if', 'for', 'while', 'try', etc.

        This function adds the block to the ast.Module at self.core_modules[0] AND adds the block to the end of the
        self.core_modules list. Any Nodes that are added to the block in future TemplateCompiler::compile_*() method
        calls are ALSO added to self.core_modules[0], because they are modifying the same object.

        The user of the TemplateCompiler instance is expected to call TemplateCompiler::close_block() when the
        end of a block is encountered.

        :param block: The block to add future expressions to
        :param start_offset: The offset for the start of the block
        :param end_offset: The offset for the end of the block
        :return:
        """
        self.add_statement(block, start_offset, end_offset)
        self.code_modules.append(block)
        self.selected_body = block.body
        self.variables.begin_scope()

    def close_block(self):
        """
        Used by a caller to signal the caller has finished parsing a block ('if', 'for', etc.).
        Removes the ast.Module from the end of the `self.code_modules` list.

        :return:
        """
        module = self.code_modules.pop()
        if not module.body:
            module.body.append(ast.Pass())

        self.variables.end_scope()
        self.selected_body = self.code_modules[-1].body

    def start_else_block(self, start_offset: int, end_offset: int):
        if not hasattr(self.code_modules[-1], "orelse"):
            raise self.syntax_error("Cannot start an else block without an if/for block", start_offset, end_offset)

        self.selected_body = self.code_modules[-1].orelse

    def finalize(self) -> ast.Module:
        assertion_error_message = (
            "There is more than one active block being parsed. "
            'Did you start compiling a block (e.g. "if", "for", etc.) '
            "and forget to call TemplateCompiler::close_block()?"
        )
        assert len(self.code_modules) == 1, assertion_error_message
        module = self.code_modules[0]
        ast.fix_missing_locations(module)
        return module

    def compile_expression(self, expr: str, offset: int) -> None:
        expression = self._compile_expression(expr, offset)
        self.append(expression, offset, offset + len(expr))

    def _compile_expression(self, expr: str, offset: int) -> ast.expr:
        """
        Compiles an expression into an Abstract Syntax Tree (AST) expression.

        The expression may contain filters, which are separated by the pipe character ('|'). Filters are applied to the
        expression from left to right. The result of the expression is passed to the first filter, and the result of
        that is passed to the second filter, and so on.

        @param expr: An expression which may contain filters
        @param offset: The offset of the start of the expression
        @return: An AST expression representing the expression
        """
        expr, *filters = expr.split("|")
        f_start_offset = offset + len(expr)

        expr, start_offset, end_offset = self.str_strip(expr, offset)
        n_expr = self._compile_node(expr, start_offset)
        self.set_location(n_expr, start_offset, end_offset)

        for filter_ in filters:
            f_start_offset += 1  # accounts for the pipe character
            n_expr = self._compile_filter(filter_, n_expr, f_start_offset)
            f_start_offset += len(filter_)

        return n_expr

    def _compile_filter(self, filter_: str, expr: ast.expr, offset: int) -> ast.expr:
        """
        Compiles a filter into an Abstract Syntax Tree (AST) expression.

        @param filter_: The filter to compile
        @param expr: The expression to apply the filter to
        @param offset: The offset of the start of the filter
        @return: An AST expression representing the filter application
        """
        filter_, start_offset, end_offset = self.str_strip(filter_, offset)
        filter_name, *args = filter_.split(":")

        if len(args) == 1:
            args = self._compile_node(f"[{args[0]}]", start_offset + len(filter_name)).elts
        elif len(args) > 1:
            raise self.syntax_error(f"Invalid Syntax", start_offset, end_offset)
        else:
            args = []

        if filter_name not in TEMPLATE_FILTERS:
            raise self.syntax_error(f"Unknown filter: {filter_name}", start_offset, start_offset + len(filter_name))

        pipe_name = f"_p_{filter_name}"
        self.variables.define(pipe_name, TEMPLATE_FILTERS[filter_name])

        args.insert(0, expr)

        n_expr: ast.Call = ast.Call(ast.Name(id=pipe_name, ctx=ast.Load()), args=args, keywords=[])
        self.set_location(n_expr, start_offset, end_offset)
        return n_expr

    def compile_legacy_expression(self, expr: str, offset: int) -> None:
        if expr[2] == "{":
            if expr[-2] == "}":
                n_expr = ast.Constant("${" + expr[3:-2] + "}", kind=None)
            else:
                n_expr = ast.Constant(expr, kind=None)
        elif expr[-2] == "}":
            n_expr = ast.Constant(expr, kind=None)
        else:
            expr, start_offset, end_offset = self.str_strip(expr[2:-1], offset + 2)
            n_expr = self._compile_node(expr, start_offset)
            self.set_location(n_expr, start_offset, end_offset)

        self.append(n_expr, offset, offset + len(expr))

    def compile_if(self, expr: str, offset: int):
        if not expr:
            raise self.syntax_error("Missing condition expression", offset, offset + len(expr))

        expr, start_offset, end_offset = self.str_strip(expr, offset + 2)
        n_expr = self._compile_node(expr, start_offset)
        block: ast.If = ast.If(n_expr, body=[], orelse=[])

        self.start_block(block, offset, end_offset)

    def compile_for(self, expr: str, offset: int):
        expr, start_offset, end_offset = self.str_strip(expr, offset)
        var_name, expr = self.split_on_whitespace(expr)

        expr, op_start_offset, _ = self.str_strip(expr, start_offset + len(var_name))
        op, container = self.split_on_whitespace(expr)

        container, c_start_offset, c_end_offset = self.str_strip(container, op_start_offset + len(op))
        var_name = var_name.strip()

        if not VAR_NAME_RE.match(var_name) or op.strip() != "in" or not container:
            raise self.syntax_error("Invalid syntax", start_offset, end_offset)

        self.variables.declare(var_name)

        block: ast.For = ast.For(
            body=[],
            orelse=[],
            target=ast.Name(id=var_name, ctx=ast.Store()),
            iter=self._compile_node(container, c_start_offset),
        )
        self.start_block(block, start_offset, end_offset)

    def compile_include(self, args: str, tag_offset: int, start_offset: int, end_offset: int) -> None:
        arg_start_offset = start_offset + 7
        indent = self.offset_to_position(tag_offset).column - 1

        node = self._compile_node(f"f({args})", arg_start_offset, -2)
        node.func = ast.Name(id=INCLUDE_VAR_NAME, ctx=ast.Load())

        has_indent = any(k.arg == "indent" for k in node.keywords)
        node.keywords.append(ast.keyword(arg="context", value=ast.Name(CONTEXT_VAR_NAME, ctx=CTX_LOAD)))
        if not has_indent:
            node.keywords.append(ast.keyword(arg="indent", value=ast.Constant(value=indent, kind=None)))

        self.set_location(node, start_offset, end_offset)
        self.set_location(node.func, start_offset, arg_start_offset)
        self.append(node, start_offset, end_offset)

    def compile_constant(self, const: str, offset: int) -> None:
        self.append(ast.Constant(value=const, kind=None), offset, offset + len(const))

    def _compile_node(self, value: str, offset: int, offset_drift: int = 0) -> ast.expr:
        lineno, offset = self.offset_to_position(offset)
        offset += offset_drift

        try:
            expr = ast.parse(value, mode="eval").body
        except SyntaxError as ex:
            if ex.lineno == 1:
                ex.offset += offset - 1

            ex.lineno += lineno - 1
            end_pos = None

            # TODO: Remove check after dropping support for Python < 3.10
            if getattr(ex, "end_lineno", None) is not None:
                if ex.end_lineno == 1:
                    ex.end_offset += offset - 1

                ex.end_lineno += lineno - 1
                end_pos = Position(ex.end_lineno, ex.end_offset)

            raise TemplateError(
                ex.msg,
                file_name=self.file_path,
                start_pos=Position(ex.lineno, ex.offset),
                end_pos=end_pos,
            ) from None

        transformer = TemplateNodeTransformer(self, lineno, offset)
        return transformer.visit(expr)

    def disallowed(self, message: str, start_position: Position, end_position: Position) -> Exception:
        return TemplateError(
            message,
            file_name=self.file_path,
            start_pos=start_position,
            end_pos=end_position,
        )

    def syntax_error(self, message: str, start_offset: int, end_offset: int) -> Exception:
        return TemplateError(
            message,
            file_name=self.file_path,
            start_pos=self.offset_to_position(start_offset),
            end_pos=self.offset_to_position(end_offset),
        )


class TemplateNodeTransformer(ast.NodeTransformer):
    def __init__(self, compiler: TemplateCompiler, initial_lineno: int, initial_offset: int):
        """
        A NodeTransformer which updates the location of nodes in an Abstract Syntax Tree. The locations are updated
        relative to the start of some source which the AST was parsed from.

        initial_lineno and initial_offset are used to update the location of nodes in the AST. The location of a node
        is updated by adding initial_lineno to the node's lineno, and adding initial_offset to the node's col_offset.
        Both initial_lineno and initial_offset are 1-based indices.

        @param compiler: The TemplateCompiler instance which is using this transformer
        @param initial_lineno: 0-based line number
        @param initial_offset: 0-based column number
        """
        self.compiler = compiler
        self.variable_refs = self.compiler.variables.refs

        self.initial_lineno = initial_lineno
        self.initial_offset = initial_offset

        self.skip_refs = False

    def update_location(self, node: ast.AST) -> None:
        if "lineno" in node._attributes:  # NOQA
            if node.lineno == 1:
                node.col_offset += self.initial_offset - 1

            if node.end_lineno == 1:
                node.end_col_offset += self.initial_offset - 1

            node.lineno += self.initial_lineno - 1
            node.end_lineno += self.initial_lineno - 1

    @staticmethod
    def node_bounds(node: ast.AST) -> tuple[Position, Position]:
        start_position = Position(node.lineno, node.col_offset + 1)
        end_position = Position(node.end_lineno, node.end_col_offset + 1)
        return start_position, end_position

    def generate_ref(self, node: ast.AST) -> bool:
        """
        Check if the node contains references to variables. If it does, add the references to the `variable_refs` field
        and return True. Else, return False.

        If self.skip_refs is True, this node is part of a branch in an AST which has already been traversed and some
        expression in this node's ancestors has been found to contain references. In this case, we do not need to check
        for references because any potential references in this node have already been added to the `variable_refs`
        field.

        @param node: The node to check for references
        @return: True if the node contains references or this self.skip_refs is True, False otherwise
        """
        if self.skip_refs:
            return True

        ref = VariableRef.from_ast_node(node)
        if ref:
            self.variable_refs[ref.name] = ref
            return True

        return False

    def generic_visit(self, node):
        self.update_location(node)
        return super().generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        self.update_location(node)

        if node.attr.startswith("_"):
            raise self.compiler.disallowed(f"Unknown attribute: {node.attr}", *self.node_bounds(node))

        self.skip_refs = self.generate_ref(node)
        node.value = self.visit(node.value)
        self.skip_refs = False
        return node

    def visit_Name(self, node: ast.Name):
        self.update_location(node)

        if node.id.startswith("_"):
            raise self.compiler.disallowed("Variable names cannot start with an underscore", *self.node_bounds(node))

        self.generate_ref(node)
        if node.id in self.compiler.variables:
            return node

        new_node = ast.Subscript(
            value=ast.Name(id=CONTEXT_VAR_NAME, ctx=CTX_LOAD),
            slice=ast.Constant(node.id, kind=None),
            ctx=CTX_LOAD,
        )
        ast.copy_location(new_node, node)
        return new_node

    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        self.update_location(node)
        node.slice = self.visit(node.slice)

        self.skip_refs = self.generate_ref(node)
        node.value = self.visit(node.value)
        self.skip_refs = False
        return node
