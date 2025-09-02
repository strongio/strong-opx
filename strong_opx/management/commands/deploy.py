import argparse
from typing import Any

from strong_opx.management.command import ProjectCommand
from strong_opx.project import Environment


class Command(ProjectCommand):
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("nodes", nargs="+", metavar="node", help="What to deploy?")

    def handle(self, environment: Environment, nodes: list[str], **options: Any):
        environment.deploy(nodes)
