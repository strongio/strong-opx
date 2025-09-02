import argparse
from typing import Any

from strong_opx.config import system_config
from strong_opx.management.command import BaseCommand
from strong_opx.management.utils import validate_project_name


class Command(BaseCommand):
    help_text = "Get or change Strong-OpX configuration"

    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument("--remove", action="store_true", default=False, help="Remove configuration instead")

        parser.add_argument(
            "--project",
            dest="project_name",
            type=validate_project_name,
            help="Project name if this config is project specific. If not specified, applies to all projects "
            "(unless overridden by project specific config).",
        )

        parser.add_argument("key", help="Configuration key")
        parser.add_argument("value", nargs="?", help="Configuration value")

    def handle(self, key: str, project_name: str = None, value=None, **options: Any):
        if project_name is None:
            config = system_config
        else:
            config = system_config.get_project_config(project_name)

        parts = key.split(".", 1)
        if len(parts) == 1:
            section = "default"
        else:
            section, key = parts

        if section not in config:
            config.add_section(section)

        if options["remove"]:
            config.remove_option(section, key)
        elif value is None:
            value = config.get(section, key, fallback=None)
            if value is not None:
                print(value)

            return
        else:
            config.set(section, key, value)

        config.save()
