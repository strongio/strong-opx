import argparse
import os
from typing import Any

from strong_opx.management.command import ProjectCommand
from strong_opx.platforms import KubernetesPlatform
from strong_opx.project import Environment


class Command(ProjectCommand):
    help_text = "Access Kubernetes Cluster Resources"
    parse_known_args = True

    examples = [
        "strong-opx k8s --project <project> --env <env> dashboard up",
    ]

    def add_arguments(self, parser: argparse.ArgumentParser):
        super().add_arguments(parser)
        parser.add_argument("--update-config", action="store_true", default=False, help="Force update kubectl config")

        parser.add_argument("plugin", help="Plugin to execute")
        parser.add_argument("operation", help="Plugin operation to execute")

    def handle(
        self,
        environment: Environment,
        update_config: bool,
        plugin: str,
        operation: str,
        additional_args: tuple[str, ...],
        **options: Any,
    ):
        platform = environment.select_platform(KubernetesPlatform)

        if update_config and os.path.exists(platform.kube_config_path):
            os.remove(platform.kube_config_path)

        if plugin is None:
            print("Available plugins:")
            for plugin_name in platform.plugins:
                print(f"  {plugin_name}")
            return

        platform.plugin(plugin).run(operation, *additional_args)
