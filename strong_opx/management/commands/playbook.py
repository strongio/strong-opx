import argparse
import os
from typing import Any

from strong_opx.exceptions import CommandError
from strong_opx.management.command import ProjectCommand
from strong_opx.platforms import GenericPlatform
from strong_opx.project import Environment, Project


class Command(ProjectCommand):
    help_text = "Run ansible playbook"
    allow_additional_args = True

    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            "playbook", help="Ansible playbook name (without extension) to run. Must be a file in playbooks/ directory"
        )
        parser.add_argument(
            "--host", nargs="*", dest="host_groups", metavar="GROUP_NAME", help="Specify hosts to deploy to"
        )
        parser.add_argument(
            "--keep-host-state-unchanged", action="store_true", default=False, help="Keep host state Unchanged"
        )
        super().add_arguments(parser)

    def handle(
        self,
        playbook: str,
        project: Project,
        environment: Environment,
        host_groups: list[str] = None,
        keep_host_state_unchanged: bool = False,
        **options: Any,
    ):
        platform = environment.select_platform(GenericPlatform)

        if host_groups:
            unknown_hosts = set(host_groups) - set(platform.hosts)
            if unknown_hosts:
                unknown_hosts = ", ".join(unknown_hosts)
                known_hosts = ", ".join(platform.hosts)
                raise CommandError(f"Unknown host groups: {unknown_hosts}. Choices: {known_hosts}")

        playbook_path = os.path.join(
            project.path,
            "playbooks",
            f"{playbook}.yml",
        )
        if not os.path.exists(playbook_path):
            raise CommandError(f"Unknown playbook: {playbook}")

        additional_args = ()
        if options["additional_args"]:
            additional_args += tuple(options["additional_args"])

        if keep_host_state_unchanged:
            platform.ansible_playbook(playbook_path, additional_args=additional_args, host_groups=host_groups)
        else:
            with platform.ensure_instances_are_running(host_groups):
                platform.ansible_playbook(playbook_path, additional_args=additional_args, host_groups=host_groups)
