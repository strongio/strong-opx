from functools import wraps
from typing import Any, Callable, Union
from unittest.mock import Mock, call, patch

import colorama


def assert_has_calls_exactly(mock: Mock, expected_calls: ["call"], any_order: bool = False):
    """
    The Mock::assert_has_calls() checks if the expected calls you provide the method are a SUBSET of the calls in
    Mock.mock_calls. You should NOT use that assertion if you want the `expected_calls` to account for ALL the calls
    in Mock.mock_calls.

    The following tests would pass, which might go against a developer's expectations:

    my_mock = Mock()
    my_mock(1)
    my_mock(2)
    my_mock(3)

    # These will all PASS
    my_mock.assert_has_calls([])
    my_mock.assert_has_calls([call(1)])
    my_mock.assert_has_calls([call(2)])
    my_mock.assert_has_calls([call(3)])
    my_mock.assert_has_calls([call(1), call(2)])
    my_mock.assert_has_calls([call(2), call(3)])

    If you were to use assert_has_calls_exactly() for all of those examples, they would all FAIL.
    """
    actual_number_of_calls = mock.call_count
    expected_number_of_calls = len(expected_calls)
    assert actual_number_of_calls == expected_number_of_calls, (
        f"Expected {expected_number_of_calls} call(s) but found {actual_number_of_calls} call(s).\n"
        f"expected_calls: {expected_calls}\n"
        f"mock_calls: {mock.mock_calls}"
    )
    mock.assert_has_calls(expected_calls, any_order=any_order)


def inject_self_to_calls(self_to_inject: Any, calls: list["call"]) -> list["call"]:
    """
    This function "injects" a value to represent the `self` parameter of an instance method. The function injects
    the `self` as the first positional argument for each call. All keyword arguments are left as-is. It will NOT
    preserve the `name` of the existing `call` tuple, though I have never seen the name used before, so it shouldn't
    matter. If it does, please update this function to handle that.

    You might use this function with parameterized tests in which the "self" object is re-created for each test
    invocation.
    """
    new_calls = list()
    for a_call in calls:
        # Each `call` object is a tuple of (name, positional arguments, keyword arguments)
        # https://docs.python.org/3.8/library/unittest.mock.html#calls-as-tuples
        args = a_call[1]
        kwargs = a_call[2]

        altered_args = (self_to_inject,) + args

        new_calls.append(call(*altered_args, **kwargs))

    return new_calls


class ColoramaPatch:
    to_patch = {
        "Style": colorama.Style,
        "Fore": colorama.Fore,
    }

    def decorate_class(self, klass: type):
        for attr in dir(klass):
            if not attr.startswith(patch.TEST_PREFIX):
                continue

            attr_value = getattr(klass, attr)
            if not hasattr(attr_value, "__call__"):
                continue

            patcher = type(self)()
            setattr(klass, attr, patcher.decorate_callable(attr_value))

        return klass

    def decorate_callable(self, func: Callable):
        @wraps(func)
        def patched(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return patched

    def __enter__(self):
        self.originals = {}

        for name, cls in self.to_patch.items():
            self.originals[cls] = dict(cls.__dict__)

            for k in cls.__dict__.keys():
                cls.__dict__[k] = "{%s.%s}" % (name, k)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for name, cls in self.to_patch.items():
            cls.__dict__.update(self.originals[cls])


def patch_colorama(func: Union[type, Callable]):
    patcher = ColoramaPatch()
    if isinstance(func, type):
        return patcher.decorate_class(func)

    return patcher.decorate_callable(func)
