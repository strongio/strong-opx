import ast
from dataclasses import dataclass
from typing import Any, Generator, Optional

from strong_opx.template.registry import SAFE_BUILTINS
from strong_opx.utils.tracking import Position

REF_SEP = "."


@dataclass(frozen=True)
class VariableRef:
    """
    Hold information about a variable reference in the code.

    :param name: The full name of the variable reference nodes separated by REF_SEP
    :param nodes: The individual nodes of the variable reference
    """

    name: str
    nodes: tuple[str, ...]

    start_pos: Position
    end_pos: Position

    @classmethod
    def from_ast_node(cls, top_node: ast.AST) -> Optional["VariableRef"]:
        """
        Extract a variable reference from an AST node. If the node is not a variable reference, None is returned.

        `VariableRef.nodes` are extracted using following rules:
        - If ast node is of type `ast.Name`, node is the name of the variable
        - If ast node is of type `ast.Attribute`, it's the nodes from value of the `ast.Attribute` joined with the
          attribute name of the `ast.Attribute`
            - nodes from value of the `ast.Attribute` are extracted recursively
            - If the value of the `ast.Attribute` has no nodes, ast node is skipped
        - If ast node is of type `ast.Subscript`, it's the nodes from value of the `ast.Subscript` joined with the
          slice value of the `ast.Subscript`
            - nodes from value of the `ast.Subscript` are extracted recursively
            - If the value of the `ast.Subscript` has no nodes, ast node is skipped
            - If slice value of the `ast.Subscript` is not a `ast.Constant`, ast `node.slice` is skipped
        - If ast node is of any other type, ast node is skipped.

        `VariableRef.name` is the nodes joined with REF_SEP
        `VariableRef.start_pos` is the start position of the top node
        `VariableRef.end_pos` is the end position of the top node. If the top node is a `ast.Subscript` and the
        slice value is not a `ast.Constant`, end position is the end position of the value node.

        :param top_node: The top node to extract the variable reference from
        :return VariableRef: The variable reference if found, None otherwise
        """
        start_position = Position(top_node.lineno, top_node.col_offset + 1)
        end_position = Position(top_node.end_lineno, top_node.end_col_offset + 1)

        def extract_ref_nodes(node: ast.AST) -> Generator[str, None, None]:
            if isinstance(node, ast.Name):
                yield node.id

            elif isinstance(node, ast.Attribute):
                value = tuple(extract_ref_nodes(node.value))  # NOQA
                if value:
                    yield from value
                    yield node.attr

            elif isinstance(node, ast.Subscript):
                value = tuple(extract_ref_nodes(node.value))  # NOQA
                if value:
                    yield from value
                    if isinstance(node.slice, ast.Constant):
                        yield str(node.slice.value)  # NOQA
                    else:
                        nonlocal end_position
                        end_position = Position(node.value.end_lineno, node.value.end_col_offset + 1)

        nodes = tuple(extract_ref_nodes(top_node))
        if not nodes:
            return None

        return VariableRef(name=REF_SEP.join(nodes), nodes=nodes, start_pos=start_position, end_pos=end_position)


class VariableStore:
    """
    A store for variables in the Template code. It keeps track of the variables declared in the code and their
    references.

    Store keeps track of the following:
    - Local variables declared in the current scope
    - Global variables declared in the code
    - References to context variables in the code
    """

    def __init__(self):
        self.locals: list[str] = []
        self.locals_bound: list[int] = [len(self.locals)]
        self.globals = {
            "__builtins__": SAFE_BUILTINS,
        }

        self.refs: dict[str, VariableRef] = {}

    def get_ref(self, name: str) -> Optional[VariableRef]:
        """
        Get the best matching variable reference that starts with `name`. If there are multiple matching
        references one with the lowest nodes will be returned.

        :param name: `REF_SEP` seperated name of the variable reference
        :return: The variable reference if found, None otherwise
        """

        nodes = tuple(name.split(REF_SEP))
        n_nodes = len(nodes)

        matching_refs = [ref for ref in self.refs.values() if ref.nodes[:n_nodes] == nodes]
        if matching_refs:
            return sorted(matching_refs, key=lambda ref: len(ref.nodes))[0]

    def begin_scope(self) -> None:
        self.locals_bound.append(len(self.locals))

    def end_scope(self) -> None:
        bound = self.locals_bound.pop()
        self.locals = self.locals[:bound]

    def declare(self, name: str) -> None:
        """
        Declare a local variable in the current scope
        :param name: The name of the variable
        """
        self.locals.append(name)

    def define(self, name: str, value: Any) -> None:
        """
        Define a global variable in the store. This is used to define additional variables in the store that are not
        present in the code. For example, template filters.

        :param name: The name of the variable
        :param value: The value of the variable
        """
        self.globals[name] = value

    def __contains__(self, name) -> bool:
        """
        Check if a variable is defined in the store.
        This checks if the variable is defined in the locals or the globals or allowed builtins.

        :param name: The name of the variable
        :return: True if the variable is defined, False otherwise
        """

        return name in self.locals or name in self.globals or name in SAFE_BUILTINS
