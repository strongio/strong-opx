from typing import TYPE_CHECKING, Any, Optional, TypeVar, Union

from strong_opx.exceptions import UndefinedVariableError, VariableError
from strong_opx.template.template import Template
from strong_opx.template.variable import REF_SEP
from strong_opx.utils.tracking import OpxMapping, OpxSequence, OpxString, get_position, set_position

if TYPE_CHECKING:
    from strong_opx.template import Context

T = TypeVar("T")
T_CONTAINER = Union[dict, list]
T_CONTAINER_INDEXER = Union[str, int]
NOT_RENDERED = object()


class TreeNode:
    __slots__ = ("value", "children")

    def __init__(self, value: Any):
        self.value = value
        self.children: list[TreeNode] = []

    def __hash__(self):
        # Note this does NOT account for self.children. So, two TreeNodes with the same 'value' will have the same hash.
        # This behavior is utilized by the check_cycle() method.
        return hash(self.value)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value})"

    def check_cycle(self, visited: dict["TreeNode", bool], in_stack: dict["TreeNode", bool]) -> Optional[list[str]]:
        # Check if node exists in the recursive stack
        if in_stack.get(self):
            return [self.value]

        # Check if node is already visited
        if visited.get(self):
            return None

        # Marking node as visited and present in recursive stack
        visited[self] = True
        in_stack[self] = True

        # Iterate for all children of node.
        for node in self.children:
            cycle_path = node.check_cycle(visited, in_stack)
            if cycle_path:
                cycle_path.append(self.value)
                return cycle_path

        # Mark 'node' to be removed from the recursive stack.
        in_stack.pop(self)
        return None


class SubstitutionBase:
    def __init__(self, ref: str):
        self.ref = ref

    def update_required_refs(self, context_refs: set) -> None:
        pass  # Does nothing by default

    def can_resolve(self, resolved_refs: set) -> bool:
        raise NotImplementedError

    def resolve(self, context: "Context") -> None:
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.ref}>"


class Substitution(SubstitutionBase):
    __slots__ = ("ref", "template", "parent", "index", "required_refs")

    def __init__(self, ref: str, template: Template, parent: T_CONTAINER, index: T_CONTAINER_INDEXER):
        self.template = template
        self.required_refs = set(self.template.variables.refs)

        self.parent = parent
        self.index = index

        super().__init__(ref)

    def update_required_refs(self, context_refs: set) -> None:
        self.required_refs = {ref for ref in self.required_refs if ref.split(REF_SEP)[0] not in context_refs}

    def can_resolve(self, resolved_refs: set) -> bool:
        return self.required_refs.issubset(resolved_refs)

    def resolve(self, context: "Context") -> None:
        rendered = self.template.render(context)
        if isinstance(rendered, str):
            rendered = OpxString(rendered)
            set_position(rendered, *get_position(self.template.value))

        self.parent[self.index] = rendered


class ContainerSubstitution(SubstitutionBase):
    __slots__ = ("ref", "obj", "parent", "index")

    def __init__(self, ref: str, obj: Union[list, dict], parent: T_CONTAINER, index: T_CONTAINER_INDEXER):
        self.obj = obj
        self.parent = parent
        self.index = index

        super().__init__(ref)

    @property
    def required_refs(self):
        return set()

    def can_resolve(self, resolved_refs: set) -> bool:
        values = self.obj
        if isinstance(self.obj, dict):
            values = self.obj.values()

        return not any(v == NOT_RENDERED for v in values)

    def resolve(self, context: "Context") -> None:
        self.parent[self.index] = self.obj


class ObjectTemplate:
    __slots__ = ("context", "substitutions")

    def __init__(self, context: "Context"):
        """
        @param context: A context which is used to render values. This context is NOT modified by this class.
        """
        self.context = context
        self.substitutions: list[Union[Substitution, ContainerSubstitution]] = []

    def render(self, value: T) -> T:
        """
        Renders the given value, substituting any variables with values from the context and/or from sub-values defined
        within the value (for example, 'value' may be a dict with sub-values that reference each other).

        Note that this method does NOT honor the frozen state of the context (self.context). If 'value' contains a
        variable that is "frozen" in the context, the variable will be overwritten when rendering 'value'.
        However, it will NOT edit the variable in the context.

        For example:
        context = { 'frozen': 'frozen value' }
        value = { 'frozen': 'new frozen value', 'uses_frozen': 'blah ${frozen}' }

        would return:
        { 'frozen': 'new frozen value', 'uses_frozen': 'blah new frozen value' }

        @param value: The value to render.
        @return: The rendered value.
        """
        if isinstance(value, list):
            rendered = self.render_sequence("", value)

        elif isinstance(value, dict):
            rendered = {}
            for k, v in value.items():
                self.render_nested(ref=k, value=v, parent=rendered, index=k)

        elif isinstance(value, str):
            rendered = Template(value).render(self.context)

        else:
            return value

        context = self.context
        update_context_on_render = False

        if isinstance(rendered, dict):
            # If the value is dict, we need to update context with the rendered value so that any subsequent
            # substitutions can use the rendered value.
            update_context_on_render = True
            context = self.context.chain()
            context.update(rendered)

        self.resolve_substitutions(context, update_context_on_render)
        return rendered

    def render_nested(self, ref: str, value: Any, parent: T_CONTAINER, index: T_CONTAINER_INDEXER) -> None:
        if isinstance(value, list):
            obj = self.render_sequence(ref, value)
            parent[index] = obj
            substitution = ContainerSubstitution(ref, obj, parent, index)

        elif isinstance(value, dict):
            obj = self.render_mapping(ref, value)
            parent[index] = obj
            substitution = ContainerSubstitution(ref, obj, parent, index)

        elif isinstance(value, str):
            template = Template(value)
            substitution = Substitution(ref=ref, template=template, parent=parent, index=index)

        else:  # No need to render the value
            parent[index] = value
            return

        # Don't render the substitution yet. We need to resolve all substitutions first.
        # Because, there might be some variable used in template that is overridden
        # but context is only updated in `resolve_substitutions()` method.
        self.substitutions.append(substitution)

    def render_sequence(self, ref: str, value: list) -> list:
        parent = OpxSequence([NOT_RENDERED] * len(value))
        set_position(parent, *get_position(value))

        for i, item in enumerate(value):
            self.render_nested(f"{ref}{REF_SEP}{i}", item, parent=parent, index=i)

        return parent

    def render_mapping(self, ref: str, value: dict[str, Any]) -> dict[str, Any]:
        parent = OpxMapping()
        set_position(parent, *get_position(value))

        for k, v in value.items():
            parent[k] = NOT_RENDERED
            self.render_nested(f"{ref}{REF_SEP}{k}", v, parent=parent, index=k)

        return parent

    def resolve_substitutions(self, context: "Context", update_context_on_render: bool) -> None:
        resolved_refs = set()
        context_refs = set(context)
        substitutions = self.substitutions

        # If any context variable is referenced in the template, we need to remove it from the resolved_refs
        # so that it can be resolved again.
        for substitution in self.substitutions:
            top_ref = substitution.ref.split(REF_SEP)[0]
            if top_ref in context_refs:
                context_refs.remove(top_ref)

        # Update required_refs for each substitution based on the context_refs
        if context_refs:
            for substitution in self.substitutions:
                substitution.update_required_refs(context_refs)

        # Repeatedly iterates over the substitutions, gradually resolving values. If we end up with substitutions that
        # cannot be resolved, call handle_deadlock() which will raise the appropriate error.
        while substitutions:
            resolved = False

            i = len(substitutions) - 1
            while i >= 0:
                substitution = substitutions[i]
                if substitution.can_resolve(resolved_refs):
                    resolved_refs.add(substitution.ref)

                    substitutions.pop(i)
                    substitution.resolve(context)

                    resolved = True
                    if update_context_on_render and "." not in substitution.ref:
                        context[substitution.index] = substitution.parent[substitution.index]

                i -= 1

            if not resolved:
                # Reached deadlock while resolving substitutions. This can be either presence of a
                # circular dependency or some variable is undefined.
                self.handle_deadlock(resolved_refs)
                break

    def handle_deadlock(self, resolved_refs: set) -> None:
        """
        Compiles the unresolved variables from each substitution. If a variable does not exist, an error is raised.
        If one or more variables create a circular dependency, an error is raised.
        """
        all_nodes: dict[str, TreeNode] = {}
        defined_refs = {s.ref for s in self.substitutions} | resolved_refs

        unknowns = set()

        # loop builds trees with each tree's root being one of the string keys from load(), and each leaf of a tree
        # being a variable that root key requires for its value to be compiled/resolved.
        for substitution in self.substitutions:
            unknowns.update(substitution.required_refs - defined_refs)

            if substitution.ref in all_nodes:
                root_node = all_nodes[substitution.ref]
            else:
                root_node = TreeNode(substitution.ref)
                all_nodes[substitution.ref] = root_node

            for require in substitution.required_refs:
                if require in all_nodes:
                    node = all_nodes[require]
                else:
                    node = TreeNode(require)
                    all_nodes[require] = node

                root_node.children.append(node)

        if unknowns:
            raise UndefinedVariableError(*unknowns)

        # With the dependency trees built, walk through and find the cyclical dependencies preventing us
        # from resolving all substitutions.
        visited = {}
        in_stack = {}

        for node in all_nodes.values():
            cycle_path = node.check_cycle(visited, in_stack)
            if cycle_path:
                cycle_path.reverse()
                raise VariableError("Found circular dependency: {}".format(" -> ".join(cycle_path)), node.value)
