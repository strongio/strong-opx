import argparse
import warnings
from typing import TYPE_CHECKING, Any

from strong_opx.exceptions import PluginError

if TYPE_CHECKING:
    from strong_opx.platforms.base import Platform


class PlatformPlugin:
    def __init__(self, platform: "Platform"):
        self.platform = platform

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        pass

    def parse_arguments(self, *args: str) -> dict[str, Any]:
        parser = argparse.ArgumentParser()
        self.add_arguments(parser)

        options = parser.parse_args(args)
        return vars(options)

    def is_installed(self) -> bool:
        raise NotImplementedError()

    def install(self) -> None:
        raise NotImplementedError()

    def run(self, operation: str, *args: str) -> None:
        operation = operation.lower()
        if operation == "install":
            if args:
                warnings.warn("Additional passed arguments will be ignored: {}".format(" ".join(args)))

            if self.is_installed():
                raise PluginError("Plugin is already installed")

            self.install()
            return

        if not self.is_installed():
            raise PluginError("Plugin is not installed and is not available. Please install it first")

        kwargs = self.parse_arguments(operation, *args)
        self.handle(**kwargs)

    def handle(self, **kwargs):
        raise NotImplementedError()
