import argparse
from typing import Any

from strong_opx.hcl import run_packer
from strong_opx.management.command import ProjectCommand
from strong_opx.project import Environment


class Command(ProjectCommand):
    help_text = "Run packer builds"
    allow_additional_args = True
    parse_known_args = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("command", help="Packer command to execute. e.g. init, fmt, build")
        super().add_arguments(parser)

    def handle(self, environment: Environment, command: str, **options: Any) -> None:
        run_packer(environment, command, *options["additional_args"])
