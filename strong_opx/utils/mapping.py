from collections import UserDict
from typing import Any, Callable, Generator, MutableMapping

from pydantic_core import CoreSchema, core_schema

NOT_SPECIFIED = object()


class LazyValue:
    def __init__(self, resolver: Callable[[], Any]):
        self.resolver = resolver

    def resolve(self) -> Any:
        return self.resolver()

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.resolver}>"


class LazyDict(MutableMapping):
    def __init__(self, *args, **kwargs):
        self._data: dict[str, Any] = dict(*args, **kwargs)

    def __missing__(self, key):
        raise KeyError(key)

    def __getitem__(self, key: str) -> Any:
        """
        Retrieves the value associated with 'key'. If the value is a `LazyValue`, that will be resolved and
        stored in the object for future use.

        @param key: Key to get value of
        @return: The value corresponding to the key
        @raise KeyError if the specified key does not exist
        """
        value = self.get(key, default=NOT_SPECIFIED)
        if value is NOT_SPECIFIED:
            return self.__missing__(key)

        return value

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Generator[str, None, None]:
        yield from self._data

    def __repr__(self) -> str:
        r = ", ".join(f"{k!r}: {self.get(k, resolve=False)!r}" for k in self)
        return f"{self.__class__.__name__}({{{r}}})"

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def set_lazy(self, key: str, resolver: Callable[[], Any]) -> None:
        """
        Set a lazy value for the specified key. The value will be resolved when it is first accessed.
        `resolver` will only be called once and the result will be cached.

        :param key: Key to set value for
        :param resolver: Function to resolve the value
        """
        self._data[key] = LazyValue(resolver)

    def get(self, key: str, default=None, resolve: bool = True) -> Any:
        """
        Retrieves the value associated with `key`. Optionally if the value is a `LazyValue`,
        that will be resolved and the results are stored and returned from get().

        @param key: Key to get value of
        @param default: Value to return if the key does not exist
        @param resolve: Whether to resolve a `LazyValue` if found
        @return: The value corresponding to the key
        """
        value = self._data.get(key, default)
        if resolve and isinstance(value, LazyValue):
            value = value.resolve()
            self._data[key] = value

        return value


class CaseInsensitiveMultiTagDict(UserDict[str, list[str]]):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update(dict(*args, **kwargs))

    def __setitem__(self, key: str, value: str) -> None:
        key = key.lower()
        if key in self.data:
            if value not in self.data[key]:
                self.data[key].append(value)
        else:
            self.data[key] = [value]

    def __getitem__(self, key: str) -> list[str]:
        return self.data[key.lower()]

    def __contains__(self, key: str) -> bool:
        return key.lower() in self.data

    def __delitem__(self, key: str) -> None:
        key = key.lower()
        if key in self.data:
            del self.data[key]
        else:
            raise KeyError(key)

    def get(self, key: str, default=NOT_SPECIFIED) -> list[str]:
        if default is NOT_SPECIFIED:
            default = []

        return self.data.get(key.lower(), default)

    @staticmethod
    def __get_pydantic_core_schema__(source_type, handler) -> CoreSchema:
        return core_schema.dict_schema(
            keys_schema=core_schema.str_schema(),
            values_schema=core_schema.union_schema(
                [core_schema.str_schema(), core_schema.list_schema(core_schema.str_schema())]
            ),
        )
