import ast
from ast import AST
from dataclasses import dataclass
from unittest import TestCase
from unittest.mock import Mock, call, create_autospec, patch

import astunparse
import pytest
from _pytest.fixtures import SubRequest
from parameterized import parameterized

from strong_opx.exceptions import TemplateError
from strong_opx.template.compiler import CTX_STORE, OUTPUT_VAR_NAME, TemplateCompiler, TemplateNodeTransformer
from strong_opx.template.variable import VariableStore
from strong_opx.utils.tracking import Position
from tests.helper_functions import assert_has_calls_exactly, inject_self_to_calls


class FakeTemplateCompiler(TemplateCompiler):

    # noinspection PyMissingConstructor
    def __init__(
        self,
        code_modules=None,
        initial_col_offset=None,
        initial_line_no=None,
        variables=None,
        value=None,
    ):
        self.file_path = "test_file_path"
        self.code_modules = code_modules
        self.selected_body = []
        self.initial_col_offset = initial_col_offset
        self.initial_line_no = initial_line_no
        self.variables = variables
        self.value = value


class TestTemplateCompiler(TestCase):
    @parameterized.expand(
        [
            ("  hello  ", 0, ("hello", 2, 7)),
            ("  hello", 0, ("hello", 2, 7)),
            ("hello ", 0, ("hello", 0, 5)),
            ("  hello  ", 10, ("hello", 12, 17)),
        ]
    )
    def test_str_strip(self, value, offset, expected_outcome):
        outcome = TemplateCompiler.str_strip(value, offset)
        self.assertEqual(outcome, expected_outcome)

    @patch.object(Position, "from_offset", autospec=True)
    def test_offset_to_position(self, position_from_offset_mock: Mock):
        subject = FakeTemplateCompiler(value="test string", initial_line_no=5, initial_col_offset=20)
        subject.offset_to_position(22)

        position_from_offset_mock.assert_called_once_with("test string", 22, 5, 20)

    @parameterized.expand(
        [
            ("hello world", ("hello", " world")),
            ("five     spaces", ("five", "     spaces")),
            ("nospace", ("nospace", "")),
            ("tab\tblah", ("tab\tblah", "")),
        ]
    )
    def test_split_on_whitespace(self, expr: str, expected_return: tuple[str, str]):
        actual_return = TemplateCompiler.split_on_whitespace(expr)
        self.assertEqual(expected_return, actual_return)

    @parameterized.expand(
        [
            (True, "lines.append(str(SOME_VAR))"),
            (False, "_opx_out_ = SOME_VAR"),
        ]
    )
    def test_as_string(self, as_string: bool, expected_src: str):
        compiler = TemplateCompiler("{{ SOME_VAR }}", as_string=as_string)
        compiler.append(ast.Name("SOME_VAR", ast.Load()), 1, 10)
        node = compiler.finalize()
        generated_src = astunparse.unparse(node).strip()
        self.assertEqual(expected_src, generated_src)

    @parameterized.expand(
        [
            ("{{ SOME_VAR }}", "lines.append(str(_opx_ctx_['SOME_VAR']))"),
            ("{{ SOME_VAR.foo }}", "lines.append(str(_opx_ctx_['SOME_VAR'].foo))"),
            ("{{ SOME_VAR.bar() }}", "lines.append(str(_opx_ctx_['SOME_VAR'].bar()))"),
            ("{{ SOME_VAR[0] }}", "lines.append(str(_opx_ctx_['SOME_VAR'][0]))"),
            ('{{ SOME_VAR["hello"] }}', "lines.append(str(_opx_ctx_['SOME_VAR']['hello']))"),
        ]
    )
    def test_compile_expression(self, expression: str, expected_src: str):
        compiler = TemplateCompiler(expression)
        compiler.compile_expression(expression, 0)
        node = compiler.finalize()
        generated_src = astunparse.unparse(node).strip()
        self.assertEqual(expected_src, generated_src)

    @parameterized.expand(
        [
            ("{{ SOME_VAR|uppercase }}", "lines.append(str(_p_uppercase(_opx_ctx_['SOME_VAR'])))"),
            ('{{ SOME_VAR|date:"%Y-%m-%d" }}', "lines.append(str(_p_date(_opx_ctx_['SOME_VAR'], '%Y-%m-%d')))"),
            ("{{ SOME_VAR|uppercase|strip }}", "lines.append(str(_p_strip(_p_uppercase(_opx_ctx_['SOME_VAR']))))"),
        ]
    )
    def test_compile_expression__filters(self, expression: str, expected_src: str):
        compiler = TemplateCompiler(expression)
        compiler.compile_expression(expression, 0)
        node = compiler.finalize()
        generated_src = astunparse.unparse(node).strip()
        self.assertEqual(expected_src, generated_src)

    def test_compile_expression__unknown_filter(self):
        expr = "{{ SOME_VAR|unknown }}"
        compiler = TemplateCompiler(expr)

        with self.assertRaises(TemplateError) as cm:
            compiler.compile_expression(expr, 0)

        self.assertEqual(cm.exception.errors[0].error, "Unknown filter: unknown")

    def test_compile_expression__invalid_filter_args(self):
        expr = '{{ SOME_VAR|some_filer:"%Y-%m-%d":123 }}'
        compiler = TemplateCompiler(expr)

        with self.assertRaises(TemplateError) as cm:
            compiler.compile_expression(expr, 0)

        self.assertEqual(cm.exception.errors[0].error, "Invalid Syntax")

    def test_compile_expression__filter_included_in_context(self):
        expr = "{{ SOME_VAR|uppercase }}"
        compiler = TemplateCompiler(expr)
        compiler.compile_expression(expr, 0)

        self.assertIn("_p_uppercase", compiler.variables.globals)
        self.assertEqual(str.upper, compiler.variables.globals["_p_uppercase"])

    @parameterized.expand(
        [
            ("${VAR_1}", "lines.append(str(_opx_ctx_['VAR_1']))"),
            ("${{VAR_1}}", "lines.append('${VAR_1}')"),
            ("${VAR_1}}", "lines.append('${VAR_1}}')"),
            ("${{VAR_1}", "lines.append('${{VAR_1}')"),
        ]
    )
    def test_compile_legacy_expression(self, expression: str, expected_src: str):
        compiler = TemplateCompiler(expression)
        compiler.compile_legacy_expression(expression, 0)
        node = compiler.finalize()
        generated_src = astunparse.unparse(node).strip()
        self.assertEqual(expected_src, generated_src)

    def test_compile_if(self):
        expr = "x == 1"
        compiler = TemplateCompiler(expr)
        compiler.compile_if(expr, 0)
        compiler.close_block()
        node = compiler.finalize()
        generated_src = astunparse.unparse(node).strip()
        self.assertEqual("if (_opx_ctx_['x'] == 1):\n    pass", generated_src)

    @patch.object(TemplateCompiler, "syntax_error", autospec=True)
    def test_compile_if_no_expr(self, syntax_error_mock: Mock):
        syntax_error_mock.side_effect = RuntimeError  # TemplateSyntaxError requires args, RuntimeError does not
        compiler = FakeTemplateCompiler()

        with self.assertRaises(RuntimeError):
            compiler.compile_if("", 0)

        syntax_error_mock.assert_called_once_with(compiler, "Missing condition expression", 0, 0)

    def test_compile_for(self):
        expr = "x in range(10)"
        compiler = TemplateCompiler(expr)
        compiler.compile_for(expr, 0)
        compiler.close_block()
        node = compiler.finalize()
        generated_src = astunparse.unparse(node).strip()
        self.assertEqual("for x in range(10):\n    pass", generated_src)

    @parameterized.expand(
        [
            ("Invalid variable name", "321var in range(10)", 19),
            ('Operator is not "in"', "x innnnnn range(10)", 19),
            ("No text after operator", "x in    ", 4),
        ]
    )
    @patch.object(TemplateCompiler, "syntax_error", autospec=True)
    def test_compile_for_errors(self, description: str, expr: str, expected_end_offset: int, syntax_error_mock: Mock):
        syntax_error_mock.side_effect = RuntimeError  # TemplateSyntaxError requires args, RuntimeError does not

        compiler = FakeTemplateCompiler()

        with self.assertRaises(RuntimeError):
            compiler.compile_for(expr, 0)

        syntax_error_mock.assert_called_once_with(compiler, "Invalid syntax", 0, expected_end_offset)

    def test_compile_constant(self):
        expr = "username is "
        compiler = TemplateCompiler(expr)
        compiler.compile_constant(expr, 0)
        node = compiler.finalize()
        generated_src = astunparse.unparse(node).strip()
        self.assertEqual("lines.append('username is ')", generated_src)

    def test_start_else_block(self):
        compiler = TemplateCompiler("{% if 1 %}IF{% else %}ELSE{% endif %}")
        compiler.start_block(ast.If(ast.Constant("1", kind=None), body=[], orelse=[]), 0, len(compiler.value))
        compiler.compile_constant("IF", 11)
        compiler.start_else_block(17, 21)
        compiler.compile_constant("ELSE", 24)
        compiler.close_block()

        node = compiler.finalize()
        generated_src = astunparse.unparse(node).strip()
        self.assertEqual("if '1':\n    lines.append('IF')\nelse:\n    lines.append('ELSE')", generated_src)

    @parameterized.expand(
        [
            ("lineno is 1, add offset", 1, 10 - 1 + 1, 100 + 20 - 1),
            ("lineno is not 1, do not add offset", 5, 10 - 1 + 5, 100),
        ]
    )
    @patch.object(TemplateCompiler, "offset_to_position", autospec=True)
    @patch("strong_opx.template.compiler.ast.parse", autospec=True)
    def test_compile_node_syntax_error(
        self,
        description: str,
        syntax_error_lineno,
        expected_lineno,
        expected_offset,
        ast_parse_mock: Mock,
        offset_to_position_mock: Mock,
    ):
        syntax_error = SyntaxError("syntax message")
        syntax_error.offset = 100
        syntax_error.lineno = syntax_error_lineno
        ast_parse_mock.side_effect = syntax_error

        offset_to_position_mock.return_value = (10, 20)  # lineno, offset

        compiler = FakeTemplateCompiler()
        with self.assertRaises(TemplateError) as actual_error:
            compiler._compile_node("some value", 5)

        self.assertEqual(actual_error.exception.errors[0].error, "syntax message")
        self.assertEqual(actual_error.exception.errors[0].start_pos, Position(expected_lineno, expected_offset))
        self.assertIsNone(actual_error.exception.errors[0].end_pos)


class TestSetLocationTest:
    @dataclass
    class Parameters:
        description: str
        node_attributes: tuple[str, ...]
        expected_node_positions: dict
        expected_offset_to_positions_calls_without_self: list["call"]

    @dataclass
    class Fixture:
        node: AST
        expected_node_positions: dict
        expected_offset_to_positions_calls: list["call"]
        offset_to_position_mock: Mock
        subject: FakeTemplateCompiler

    @pytest.fixture(
        ids=lambda x: x.description,
        params=[
            Parameters(
                description="lineno is an attribute, so update the position",
                node_attributes=("lineno",),  # subclasses of AST have this field set automatically; we fake it here
                expected_node_positions={"lineno": 0, "col_offset": 1, "end_lineno": 2, "end_col_offset": 3},
                expected_offset_to_positions_calls_without_self=[call(100), call(200)],
            ),
            Parameters(
                description="lineno is NOT an attribute, so do nothing",
                node_attributes=(),
                expected_node_positions={},
                expected_offset_to_positions_calls_without_self=[],
            ),
        ],
    )
    @patch.object(TemplateCompiler, "offset_to_position", autospec=True)
    def setup(self, offset_to_position_mock: Mock, request: SubRequest) -> Fixture:
        params: TestSetLocationTest.Parameters = request.param
        start_position = Position(0, 1)
        end_position = Position(2, 3)

        offset_to_position_mock.side_effect = [start_position, end_position]

        node = AST()
        # noinspection PyClassVar
        node._attributes = params.node_attributes
        subject = FakeTemplateCompiler()
        subject.set_location(node, 100, 200)

        expected_offset_to_positions_calls = inject_self_to_calls(
            subject, params.expected_offset_to_positions_calls_without_self
        )

        return self.Fixture(
            expected_node_positions=params.expected_node_positions,
            expected_offset_to_positions_calls=expected_offset_to_positions_calls,
            node=node,
            offset_to_position_mock=offset_to_position_mock,
            subject=subject,
        )

    def test_should_call_offset_to_position(self, setup: Fixture):
        assert_has_calls_exactly(
            mock=setup.offset_to_position_mock, expected_calls=setup.expected_offset_to_positions_calls
        )

    def test_should_set_the_correct_positions_on_the_node(self, setup: Fixture):
        keys_to_compare = {"lineno", "col_offset", "end_lineno", "end_col_offset"}

        actual = {key: value for key, value in setup.node.__dict__.items() if key in keys_to_compare}

        TestCase().assertDictEqual(setup.expected_node_positions, actual)


class TestAddStatement:
    @dataclass
    class Fixture:
        set_location_mock: Mock
        subject: FakeTemplateCompiler
        value: ast.stmt

    @pytest.fixture
    @patch.object(TemplateCompiler, "set_location", autospec=True)
    def setup(self, set_location_mock: Mock) -> Fixture:
        value = ast.stmt()

        subject = FakeTemplateCompiler()
        subject.selected_body = []
        subject.add_statement(value, 0, 100)

        return self.Fixture(set_location_mock=set_location_mock, subject=subject, value=value)

    def test_should_call_set_location(self, setup: Fixture):
        setup.set_location_mock.assert_called_once_with(setup.subject, setup.value, 0, 100)

    def test_should_update_selected_body(self, setup: Fixture):
        TestCase().assertListEqual([setup.value], setup.subject.selected_body)


class TestAppend:
    @dataclass
    class Fixture:
        add_statement_mock: Mock
        ast_assign_constructor_mock: Mock
        ast_assign_instance_mock: Mock
        ast_name_constructor_mock: Mock
        ast_name_instance_mock: Mock
        subject: FakeTemplateCompiler
        value: Mock

    @pytest.fixture
    @patch("strong_opx.template.compiler.ast.Name", autospec=True)
    @patch("strong_opx.template.compiler.ast.Assign", autospec=True)
    @patch.object(TemplateCompiler, "add_statement", autospec=True)
    def setup(
        self, add_statement_mock: Mock, ast_assign_constructor_mock: Mock, ast_name_constructor_mock: Mock
    ) -> Fixture:
        value = create_autospec(spec=ast.AST, instance=True)

        subject = FakeTemplateCompiler()
        subject.append(value, 0, 100)
        return self.Fixture(
            add_statement_mock=add_statement_mock,
            ast_assign_constructor_mock=ast_assign_constructor_mock,
            ast_assign_instance_mock=ast_assign_constructor_mock.return_value,
            ast_name_constructor_mock=ast_name_constructor_mock,
            ast_name_instance_mock=ast_name_constructor_mock.return_value,
            subject=subject,
            value=value,
        )

    def test_should_create_a_name_instance(self, setup: Fixture):
        setup.ast_name_constructor_mock.assert_called_once_with(id=OUTPUT_VAR_NAME, ctx=CTX_STORE)

    def test_should_create_an_assign_instance(self, setup: Fixture):
        setup.ast_assign_constructor_mock.assert_called_once_with(
            targets=[setup.ast_name_instance_mock], value=setup.value
        )

    def test_should_add_the_assign_instance(self, setup: Fixture):
        setup.add_statement_mock.assert_called_once_with(setup.subject, setup.ast_assign_instance_mock, 0, 100)


class TestStartBlock:
    @dataclass
    class Fixture:
        add_statement_mock: Mock
        block: Mock
        subject: FakeTemplateCompiler

    @pytest.fixture
    @patch.object(TemplateCompiler, "add_statement", autospec=True)
    def setup(self, add_statement_mock: Mock):
        block = create_autospec(spec=ast.stmt, instance=True, body=[])
        variables = VariableStore()
        variables.locals.extend(["one", "two", "three"])

        subject = FakeTemplateCompiler(code_modules=[], variables=variables)
        subject.start_block(block=block, start_offset=0, end_offset=100)

        return self.Fixture(add_statement_mock=add_statement_mock, block=block, subject=subject)

    def test_should_call_add_statement(self, setup: Fixture):
        setup.add_statement_mock.assert_called_once_with(setup.subject, setup.block, 0, 100)

    def test_should_append_the_block_to_code_modules(self, setup: Fixture):
        assert setup.subject.code_modules == [setup.block]

    def test_should_update_locals_bound(self, setup: Fixture):
        assert setup.subject.variables.locals_bound == [0, 3]

    def test_should_update_selected_body(self, setup: Fixture):
        # Should be same object
        assert id(setup.subject.selected_body) == id(setup.subject.code_modules[-1].body)


class TestCloseBlock:
    pass_mock = create_autospec(spec=ast.Pass, instance=True)
    some_body_entry = create_autospec(ast.stmt, instance=True)

    @dataclass
    class Parameters:
        description: str
        code_module: Mock
        expected_code_module_body: list

    @dataclass
    class Fixture:
        code_module: Mock
        expected_code_module_body: list
        expected_code_modules: list[Mock]
        subject: FakeTemplateCompiler

    @pytest.fixture(
        ids=lambda x: x.description,
        params=[
            Parameters(
                description="entry does NOT have body, so add Pass",
                code_module=create_autospec(spec=ast.stmt, instance=True, body=[]),
                expected_code_module_body=[pass_mock],
            ),
            Parameters(
                description="entry DOES have body, so do NOT add Pass",
                code_module=create_autospec(spec=ast.stmt, instance=True, body=[some_body_entry]),
                expected_code_module_body=[some_body_entry],
            ),
        ],
    )
    @patch("strong_opx.template.compiler.ast.Pass", autospec=True)
    def setup(self, pass_constructor_mock: Mock, request: SubRequest):
        params: TestCloseBlock.Parameters = request.param

        pass_constructor_mock.return_value = self.pass_mock

        first_module = create_autospec(spec=ast.Module, instance=True, body=[])
        variables = VariableStore()
        variables.locals = ["one", "two", "three"]
        variables.locals_bound = [0, 2]

        subject = FakeTemplateCompiler(code_modules=[first_module, params.code_module], variables=variables)

        subject.close_block()

        return self.Fixture(
            code_module=params.code_module,
            expected_code_module_body=params.expected_code_module_body,
            expected_code_modules=[first_module],
            subject=subject,
        )

    def test_remove_the_entry_from_code_modules(self, setup: Fixture):
        assert setup.subject.code_modules == setup.expected_code_modules

    def test_entry_should_have_expected_body(self, setup: Fixture):
        assert setup.code_module.body == setup.expected_code_module_body

    def test_should_remove_block_vars_from_local_vars(self, setup: Fixture):
        assert setup.subject.variables.locals == ["one", "two"]

    def test_should_update_selected_body(self, setup: Fixture):
        # Should be same object
        assert id(setup.subject.selected_body) == id(setup.subject.code_modules[-1].body)


class TestFinalize:
    @dataclass
    class Fixture:
        actual_return: ast.Module
        code_module: Mock
        fix_missing_locations_mock: Mock

    @pytest.fixture
    @patch("strong_opx.template.compiler.ast.fix_missing_locations", autospec=True)
    def setup(self, fix_missing_locations_mock: Mock):
        code_module = create_autospec(spec=ast.Module, instance=True)

        subject = FakeTemplateCompiler(code_modules=[code_module])
        actual_return = subject.finalize()

        return self.Fixture(
            actual_return=actual_return, code_module=code_module, fix_missing_locations_mock=fix_missing_locations_mock
        )

    def test_should_call_fix_missing_locations(self, setup: Fixture):
        setup.fix_missing_locations_mock.assert_called_once_with(setup.code_module)

    def test_should_return_the_expected_value(self, setup: Fixture):
        assert setup.code_module == setup.actual_return

    def test_should_raise_an_error_if_code_modules_has_more_than_one_entry(self):
        subject = FakeTemplateCompiler(code_modules=[1, 2])

        with pytest.raises(AssertionError) as cm:
            subject.finalize()

        assert str(cm.value).startswith("There is more than one active block")


class TemplateNodeTransformerTests(TestCase):
    @parameterized.expand(
        [
            # Name
            ("a", ["a"]),
            ("a()", ["a"]),
            ("a(b, c)", ["a", "b", "c"]),
            ("a + b", ["a", "b"]),
            # Attribute
            ("a.b", ["a.b"]),
            ("a.b.c()", ["a.b.c"]),
            ("a.b.c", ["a.b.c"]),
            ("a.b + b.c", ["a.b", "b.c"]),
            ("a().b", ["a"]),
            ("a(b.c, d).b", ["a", "b.c", "d"]),
            # Subscript
            ("a[0]", ["a.0"]),
            ("a()[0]", ["a"]),
            ("a.b()[0]", ["a.b"]),
            ("a.b(b)[0]", ["a.b", "b"]),
            ("a['b']", ["a.b"]),
            ("a[0][1]", ["a.0.1"]),
            ("a[0] + b[1]", ["a.0", "b.1"]),
            ("a[b]", ["a", "b"]),
            ("a[0].b", ["a.0.b"]),
            ("a[0][b]", ["a.0", "b"]),
        ]
    )
    def test_refs(self, code, expected_variables):
        variables = VariableStore()
        compiler = Mock(spec=TemplateCompiler, variables=variables)
        extractor = TemplateNodeTransformer(compiler, initial_lineno=1, initial_offset=1)
        extractor.visit(ast.parse(code))

        self.assertEqual(len(variables.refs), len(expected_variables))
        for expected_v in expected_variables:
            self.assertIn(expected_v, variables.refs)

    @parameterized.expand(
        [
            # Name
            ("a", "a", Position(1, 2)),
            ("a()", "a", Position(1, 2)),
            # # Attribute
            ("a.b", "a.b", Position(1, 4)),
            ("a.b.c()", "a.b.c", Position(1, 6)),
            # Subscript
            ("a[0]", "a.0", Position(1, 5)),
            ("a['b']", "a.b", Position(1, 7)),
            ("a[0][1]", "a.0.1", Position(1, 8)),
            ("a[b]", "a", Position(1, 2)),
            ("a[0].b", "a.0.b", Position(1, 7)),
            ("a[0][b]", "a.0", Position(1, 5)),
        ]
    )
    def test_ref_location(self, code, expected_variable, expected_end_position):
        variables = VariableStore()
        compiler = Mock(spec=TemplateCompiler, variables=variables)
        extractor = TemplateNodeTransformer(compiler, initial_lineno=1, initial_offset=1)
        extractor.visit(ast.parse(code))

        ref = variables.refs[expected_variable]
        self.assertEqual(ref.start_pos, Position(1, 1))
        self.assertEqual(ref.end_pos, expected_end_position)
