import argparse
from typing import Any

from strong_opx.hcl import run_terraform
from strong_opx.management.command import ProjectCommand
from strong_opx.project import Environment


class Command(ProjectCommand):
    help_text = "Execute Terraform command for specified environment"
    allow_additional_args = True
    parse_known_args = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("command", help="Terraform command to execute. e.g. init, plan")
        super().add_arguments(parser)

    def handle(self, environment: Environment, command: str, **options: Any):
        run_terraform(environment, command, *options["additional_args"])
