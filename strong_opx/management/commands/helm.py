import argparse
from typing import Any

from strong_opx.helm import HelmManager
from strong_opx.management.command import ProjectCommand
from strong_opx.platforms import KubernetesPlatform
from strong_opx.project import Environment


class Command(ProjectCommand):
    help_text = "Manage Helm Charts"
    allow_additional_args = True

    examples = [
        "strong-opx helm --project <project> --env <env> apply",
        "strong-opx helm --project <project> --env <env> apply --upgrade",
        "strong-opx helm --project <project> --env <env> apply --prune",
        "strong-opx helm --project <project> --env <env> -- uninstall <helm_chart_name>",
    ]

    def add_arguments(self, parser: argparse.ArgumentParser):
        super().add_arguments(parser)
        subparsers = parser.add_subparsers(title="operation", description="Operation to execute")

        apply = subparsers.add_parser("apply", help="Upgrade/install all charts")
        apply.add_argument("--prune", action="store_true", default=False, help="Uninstall removed packages")
        apply.add_argument("--upgrade", action="store_true", default=False, help="Upgrade installed packages")
        apply.add_argument("charts", metavar="chart", nargs="*", help="Specify charts to apply")
        apply.set_defaults(operation="apply")

    def handle(self, environment: Environment, additional_args: tuple[str, ...], operation: str = None, **options: Any):
        platform = environment.select_platform(KubernetesPlatform)

        manager = HelmManager(platform)
        if operation is None:
            manager.run(*additional_args)

        if operation == "apply":
            manager.apply(upgrade=options["upgrade"], charts=options["charts"], additional_args=additional_args)
            if options["prune"]:
                manager.prune(*additional_args)
