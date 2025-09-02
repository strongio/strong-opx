import argparse
import os
from typing import Any

from strong_opx.management.command import ProjectCommand
from strong_opx.platforms import KubernetesPlatform
from strong_opx.project import Environment


class Command(ProjectCommand):
    help_text = "Manage Kubernetes Cluster"
    allow_additional_args = True
    parse_known_args = True

    examples = [
        "strong-opx kubectl --project <project> --env <env> -- apply -f <file>.yml",
    ]

    def add_arguments(self, parser: argparse.ArgumentParser):
        super().add_arguments(parser)
        parser.add_argument("--update-config", action="store_true", default=False, help="Force update kubectl config")

    def handle(self, environment: Environment, additional_args: tuple[str, ...], update_config: bool, **options: Any):
        platform = environment.select_platform(KubernetesPlatform)

        if update_config and os.path.exists(platform.kube_config_path):
            os.remove(platform.kube_config_path)

        platform.kubectl(*additional_args)
