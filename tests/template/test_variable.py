import ast
from unittest import TestCase

import pytest
from parameterized import parameterized

from strong_opx.template.variable import REF_SEP, VariableRef, VariableStore
from strong_opx.utils.tracking import Position


class FakeVariableRef(VariableRef):
    def __init__(self, nodes: tuple[str, ...]):
        super().__init__(name=REF_SEP.join(nodes), nodes=nodes, start_pos=None, end_pos=None)


class TestVariableRef:
    class TestFromAstNode:
        @pytest.mark.parametrize(
            argnames=["top_node", "expected_return"],
            argvalues=[
                # Simple, single-node inputs
                pytest.param(
                    ast.Constant(value="var", kind=None, lineno=1, col_offset=0, end_lineno=1, end_col_offset=3),
                    None,
                    id='"var": Constant node, return None',
                ),
                pytest.param(
                    ast.Name(id="var", ctx=ast.Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3),
                    VariableRef(
                        name="var",
                        nodes=("var",),
                        start_pos=Position(line=1, column=1),
                        end_pos=Position(line=1, column=4),
                    ),
                    id="var: Name node, return a VariableRef",
                ),
                pytest.param(
                    ast.Attribute(
                        value=ast.Name(
                            id="var", ctx=ast.Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3
                        ),
                        attr="attr",
                        ctx=ast.Load(),
                        lineno=1,
                        col_offset=0,
                        end_lineno=1,
                        end_col_offset=8,
                    ),
                    VariableRef(
                        name="var.attr",
                        nodes=("var", "attr"),
                        start_pos=Position(line=1, column=1),
                        end_pos=Position(line=1, column=9),
                    ),
                    id="var.attr: Attribute node, return a VariableRef",
                ),
                pytest.param(
                    ast.Subscript(
                        value=ast.Name(
                            id="var", ctx=ast.Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3
                        ),
                        slice=ast.Constant(
                            value="slice", kind=None, lineno=1, col_offset=0, end_lineno=1, end_col_offset=8
                        ),
                        ctx=ast.Load(),
                        lineno=1,
                        col_offset=0,
                        end_lineno=1,
                        end_col_offset=9,
                    ),
                    VariableRef(
                        name="var.slice",
                        nodes=("var", "slice"),
                        start_pos=Position(line=1, column=1),
                        end_pos=Position(line=1, column=10),
                    ),
                    id='var["slice"]: Subscript node with constant slice, return a VariableRef',
                ),
                pytest.param(
                    ast.Subscript(
                        value=ast.Name(
                            id="var", ctx=ast.Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3
                        ),
                        slice=ast.Slice(
                            lower=ast.Constant(value=1),
                            upper=ast.Constant(value=2),
                        ),
                        ctx=ast.Load(),
                        lineno=1,
                        col_offset=0,
                        end_lineno=1,
                        end_col_offset=5,
                    ),
                    VariableRef(
                        name="var",
                        nodes=("var",),
                        start_pos=Position(line=1, column=1),
                        end_pos=Position(line=1, column=4),
                    ),
                    id=(
                        "var[1:2]: Subscript node with slice slice, returns VariableRef for var only. var[1:2] is the "
                        "same as var[1], but var[1] returns a VariableRef for var[1]"
                    ),
                ),
                pytest.param(
                    ast.Subscript(
                        value=ast.Name(
                            id="var", ctx=ast.Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3
                        ),
                        slice=ast.Constant(value=1),
                        ctx=ast.Load(),
                        lineno=1,
                        col_offset=0,
                        end_lineno=1,
                        end_col_offset=6,
                    ),
                    VariableRef(
                        name="var.1",
                        nodes=("var", "1"),
                        start_pos=Position(line=1, column=1),
                        end_pos=Position(line=1, column=7),
                    ),
                    id=(
                        "var[1]: Subscript node with constant slice, return VariableRef. var[1:2] is the same as "
                        "var[1], but var[1:2] returns None while var[1] returns a VariableRef"
                    ),
                ),
                # Complex, multi-node inputs
                pytest.param(
                    ast.Attribute(
                        value=ast.Attribute(
                            value=ast.Name(
                                id="var", ctx=ast.Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3
                            ),
                            attr="attr",
                            ctx=ast.Load(),
                            lineno=1,
                            col_offset=0,
                            end_lineno=1,
                            end_col_offset=8,
                        ),
                        attr="attr2",
                        ctx=ast.Load(),
                        lineno=1,
                        col_offset=0,
                        end_lineno=1,
                        end_col_offset=8,
                    ),
                    VariableRef(
                        name="var.attr.attr2",
                        nodes=("var", "attr", "attr2"),
                        start_pos=Position(line=1, column=1),
                        end_pos=Position(line=1, column=9),
                    ),
                    id="Nested Attribute nodes, return a VariableRef",
                ),
                pytest.param(
                    ast.Attribute(
                        value=ast.Subscript(
                            value=ast.Name(
                                id="a", ctx=ast.Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=1
                            ),
                            slice=ast.Constant(value="b"),
                            ctx=ast.Load(),
                        ),
                        attr="c",
                        ctx=ast.Load(),
                        lineno=1,
                        col_offset=0,
                        end_lineno=1,
                        end_col_offset=7,
                    ),
                    VariableRef(
                        name="a.b.c",
                        nodes=("a", "b", "c"),
                        start_pos=Position(line=1, column=1),
                        end_pos=Position(line=1, column=8),
                    ),
                    id="a[b].c: Nested Attribute nodes, return a VariableRef",
                ),
            ],
        )
        def test_should_return_variable_ref_from_ast_node(self, top_node, expected_return):
            assert VariableRef.from_ast_node(top_node) == expected_return


class VariableStoreTests(TestCase):
    @parameterized.expand(
        [
            ([], "unknown", None),
            ([FakeVariableRef(("a",))], "a", "a"),
            ([FakeVariableRef(("ab",))], "a", None),
            ([FakeVariableRef(("a", "b"))], "a", "a.b"),
            ([FakeVariableRef(("a",)), FakeVariableRef(("a", "b"))], "a", "a"),
        ]
    )
    def test_get_ref(self, all_refs: list[VariableRef], lookup_name: str, expected_ref_name: str):
        store = VariableStore()
        for ref in all_refs:
            store.refs[ref.name] = ref

        found_ref = store.get_ref(lookup_name)
        found_ref_name = found_ref.name if found_ref else None
        self.assertEqual(found_ref_name, expected_ref_name)
