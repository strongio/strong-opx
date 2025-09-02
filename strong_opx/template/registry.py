import datetime
from typing import Callable


def datetime_filter(value, fmt):
    if not isinstance(value, (datetime.datetime, datetime.date)):
        raise ValueError(f"Expected a datetime object, got {type(value).__name__}")

    return value.strftime(fmt)


SAFE_BUILTINS: dict[str, Callable] = {
    "range": range,
    "str": str,
}

TEMPLATE_FILTERS: dict[str, Callable] = {
    "uppercase": str.upper,
    "lowercase": str.lower,
    "titlecase": str.title,
    "strip": str.strip,
    "datetime": datetime_filter,
    "date": datetime_filter,
}
