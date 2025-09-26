from typing import Optional

from pydantic import ValidationError

from strong_opx.exceptions import ErrorDetail, YAMLError
from strong_opx.utils.tracking import Position, get_position

ERROR_MESSAGE_BY_TYPE = {
    "missing": "Missing required field",
}


def get_position_by_path(
    input_values: dict, path: tuple
) -> tuple[Optional[str], Optional[Position], Optional[Position]]:
    parent = None
    current = input_values
    for part in path:
        parent = current
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None, None, None

    position = get_position(current)
    if position[0] is None:
        actual_key = next((k for k in parent.keys() if k == path[-1]), None)
        return get_position(actual_key)

    return position


def translate_pydantic_errors(input_values: dict, ex: ValidationError) -> Exception:
    translated = []

    for error in ex.errors():
        file_name = get_position(input_values)[0]
        _, start_offset, end_offset = get_position_by_path(input_values, error["loc"])
        message = ERROR_MESSAGE_BY_TYPE.get(error["type"], error["msg"])

        if start_offset is None:
            loc = " > ".join(error["loc"])
            message = f"{loc}: {message}"

        translated.append(
            ErrorDetail(
                error=message,
                file_path=file_name,
                start_pos=start_offset,
                end_pos=end_offset,
            )
        )

    return YAMLError(translated)
