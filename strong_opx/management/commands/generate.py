import argparse
import importlib.util
from typing import TYPE_CHECKING, Any

from strong_opx.exceptions import CommandError
from strong_opx.management.command import ProjectCommand

if TYPE_CHECKING:
    from strong_opx.project import Project


class Command(ProjectCommand):
    require_environment = False

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("what", help="What to generate")

    def handle(self, project: "Project", what: str, **options: Any) -> None:
        try:
            module = importlib.import_module(f"strong_opx.codegen.generators.{what}")
            generator_class = getattr(module, "Generator")
        except ModuleNotFoundError:
            raise CommandError(f"Unknown generator: {what}")

        generator = generator_class(project)
        generator.generate()
