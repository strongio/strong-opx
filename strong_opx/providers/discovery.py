import importlib
import pkgutil
import warnings
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Optional, Type, TypeVar

from colorama import Style

from strong_opx.exceptions import ConfigurationError, ErrorDetail, ImproperlyConfiguredError
from strong_opx.utils.module_loading import import_string
from strong_opx.utils.tracking import get_position

if TYPE_CHECKING:
    from strong_opx.providers import Provider

T = TypeVar("T")

_selected_provider_name: Optional[str] = None


@lru_cache()
def known_providers() -> tuple[str, ...]:
    root_module = importlib.import_module("strong_opx.providers")
    root_module_path = root_module.__path__

    providers = [name for _, name, is_package in pkgutil.iter_modules(root_module_path) if is_package]

    return tuple(providers)


def get_provider_class(provider_name: str) -> type["Provider"]:
    try:
        module = importlib.import_module(f"strong_opx.providers.{provider_name}")
    except ImportError as e:
        raise ConfigurationError(
            ErrorDetail(
                f"Failed to load {provider_name} provider module because '{e.name}' is not installed",
                hint=(
                    "Check if the strong-opx is installed correctly alongside all required external dependencies.\n\n"
                    f"    {Style.BRIGHT}pip install strong-opx[{provider_name}]{Style.RESET_ALL}"
                ),
                *get_position(provider_name),
            )
        )

    provider_class_name = getattr(module, "provider_class")
    provider_class = import_string(provider_class_name)
    setattr(provider_class, "name", provider_name)
    return provider_class


def select_provider(config_dict: dict[str, Any]) -> tuple[str, type["Provider"]]:
    found_providers = []

    # We need to keep tracking info attached with config_keys to provide better error messages.
    # While rewriting make sure tracking info is not lost.
    for config_key in config_dict.keys():
        if config_key in known_providers():
            found_providers.append(config_key)

    if len(found_providers) == 0:
        warnings.warn(
            "No provider is specified. Defaulting to `aws`. Include `aws:` in strong-opx.yml to suppress this warning"
        )
        provider_name = "aws"
    elif len(found_providers) > 1:
        raise ImproperlyConfiguredError("Multiple providers are specified. This is not allowed.")
    else:
        provider_name = found_providers.pop()

    # Replace None with empty dictionary
    if config_dict.get(provider_name) is None:
        config_dict[provider_name] = {}

    global _selected_provider_name
    _selected_provider_name = provider_name

    return provider_name, get_provider_class(provider_name)


def current_provider_name() -> str:
    if _selected_provider_name is None:
        raise RuntimeError("`current_provider_name` is called before `select_provider`")

    return _selected_provider_name


@lru_cache()
def current_provider_class() -> Type["Provider"]:
    return get_provider_class(current_provider_name())


@lru_cache()
def current_provider() -> "Provider":
    from strong_opx.project import Project

    return Project.current().provider


def current_provider_error_handler(ex: Exception) -> None:
    from strong_opx.project import Project

    project = Project.current()
    if project is None:
        raise ex

    project.provider.handle_error(ex)
