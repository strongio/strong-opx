import importlib
import logging
from importlib import import_module

logger = logging.getLogger(__name__)


def import_string(dotted_path: str):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    try:
        module = import_module(module_path, class_name)
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError(f'Module "{module_path}" does not define a "{class_name}" attribute/class') from err


def import_module_attr_if_exists(module_name: str, attr_name: str):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name != module_name:
            raise

        return None

    try:
        return getattr(module, attr_name)
    except AttributeError:
        logger.warning(f"{attr_name} not found in {module_name}. Please check the module.")
