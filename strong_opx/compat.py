try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        def __new__(cls, value):
            if not isinstance(value, str):
                raise TypeError(f"Value {value!r} is not a string")

            obj = str.__new__(cls, value)
            obj._value_ = value
            return obj

        def __str__(self):
            return self._value_
