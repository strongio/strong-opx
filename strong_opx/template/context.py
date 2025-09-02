import weakref
from collections import ChainMap
from typing import Any

from strong_opx import yaml
from strong_opx.exceptions import UndefinedVariableError, VariableError
from strong_opx.template.object_template import ObjectTemplate
from strong_opx.utils.mapping import LazyDict


class Context(LazyDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for k, v in self._data.items():
            if callable(v):
                self.set_lazy(k, v)

        self._children: list[weakref.ref] = []

    def __missing__(self, key):
        raise UndefinedVariableError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self:
            # If the key already exists in the current context, we need to update all
            # children contexts to have old value. Otherwise, they will get the new value
            # from the parent context

            current_value = self._data[key]
            i = len(self._children) - 1

            while i >= 0:
                child_ref = self._children[i]
                child = child_ref()
                if child is None:
                    # Child has been garbage collected. Remove it from the list
                    self._children.pop(i)
                else:
                    child._data[key] = current_value

                i -= 1

        if callable(value):
            self.set_lazy(key, value)
        else:
            super().__setitem__(key, value)

    def __delitem__(self, key) -> None:
        """
        Deleting variables is not supported for two reasons:
        1. As of now, there is no known use case for deleting variables from a Context
        2. A Context may use a ChainMap to store data, and deleting a variable from a ChainMap would require some
           extra thought on how we would want to handle that. Should we delete the variable from "parent" and/or "child"
           chains? Should we just set the value to None in the first map of the ChainMap? If we set to None, then how
           should the 'in' operator behave; should "deleted_key in context" return False or True? There are a lot of
           questions that need to be answered before we can implement this feature (a feature that is not needed now).

        :param key: Key to delete
        :return: (None)
        :raise: Raises a NotImplementedError
        """
        raise NotImplementedError("Deleting variables is not supported")

    @property
    def initial_vars(self) -> set[str]:
        """
        Returns the set of "initial variables" in the current Context. Initial variables are the system variables
        that are defined in the first Context, and are not inherited/chained from any other Context.

        This method returns an empty set when this Context does not use a ChainMap for self._data. The Context used
        to represent the system variables is expected to use a dict for self._data, and will therefore return an empty
        set from this method.

        :return: Set of initial variables
        """
        if isinstance(self._data, ChainMap):
            return set(self._data.maps[-1])

        return set()

    def chain(self) -> "Context":
        context = type(self)()
        self._children.append(weakref.ref(context))

        if isinstance(self._data, ChainMap):
            context._data = self._data.new_child(context._data)
        else:
            context._data = ChainMap(context._data, self._data)
        return context

    def as_dict(self, exclude_initial: bool = False) -> dict[str, Any]:
        if exclude_initial:
            initial_vars = self.initial_vars
            return {k: self[k] for k in self if k not in initial_vars}

        return dict(self)

    def require(self, *names) -> dict[str, Any]:
        unknowns = []
        resolved = {}

        for n in names:
            if n in self:
                resolved[n] = self[n]
            else:
                unknowns.append(n)

        if unknowns:
            raise UndefinedVariableError(*unknowns)

        return resolved

    def load_from_file(self, file_path: str) -> None:
        vars_ = yaml.load(file_path)
        if vars_:
            vars_ = ObjectTemplate(self).render(vars_)
            initial_vars = self.initial_vars
            for k, v in vars_.items():
                if k in initial_vars:
                    raise VariableError(f"{k} is protected variable and cannot be altered.", var_name=k)

                self[k] = v
