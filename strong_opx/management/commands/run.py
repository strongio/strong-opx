import argparse
import itertools
import logging
import os
import shlex
import time
from subprocess import CompletedProcess
from typing import Any, Optional

from strong_opx.exceptions import CommandError
from strong_opx.management.command import ProjectCommand
from strong_opx.platforms import GenericPlatform
from strong_opx.project import Environment, Project
from strong_opx.utils.shell import shell

logger = logging.getLogger(__name__)


def remote_exec(project: Project, ssh_host: str, script: str, use_screen: bool, session: str) -> CompletedProcess:
    if use_screen:
        executable = ("screen", "-S", session)
    else:
        executable = ("bash", "-c")

    return shell(
        (
            "ssh",
            "-ti",
            project.config.ssh_key,
            f"{project.config.ssh_user}@{ssh_host}",
            *executable,
            script,
        )
    )


class Command(ProjectCommand):
    help_text = "Execute local script on remote machine"
    allow_additional_args = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)

        parser.add_argument("script", nargs="?", help="Script to execute")
        parser.add_argument(
            "--session", default="default", help="An arbitrary name for this session. Session name should be unique"
        )
        parser.add_argument("--attach", default=False, action="store_true", help="Restore existing session")
        parser.add_argument(
            "--no-screen",
            default=True,
            dest="use_screen",
            action="store_false",
            help="Do not run inside screen session",
        )
        parser.add_argument(
            "--sync-only", default=False, dest="sync_only", action="store_true", help="Just sync files with remote"
        )
        parser.add_argument(
            "--host",
            help="Hostname or IP on which to execute. If not specified, defaults to first hosts in environment",
        )
        parser.add_argument(
            "--context", help="Path to directory use as context. If not specified, defaults to script parent directory"
        )

    def handle(
        self,
        project: Project,
        environment: Environment,
        script: str,
        attach: bool,
        sync_only: bool,
        use_screen: bool,
        context: Optional[str],
        host: Optional[str],
        session: Optional[str],
        additional_args: tuple[str, ...],
        **options: Any,
    ):
        platform = environment.select_platform(GenericPlatform)

        if host:
            instance = platform.resolve_instance(host)[0]
        else:
            instance = next(itertools.chain.from_iterable(platform.hosts.values()), None)
            if instance is None:
                raise CommandError("No host in environment")

        ssh_host = platform.get_ssh_host(instance)

        if attach:
            return shell(
                (
                    "ssh",
                    "-ti",
                    project.config.ssh_key,
                    f"{project.config.ssh_user}@{ssh_host}",
                    "screen",
                    "-rS",
                    session,
                )
            )

        if not script:
            raise CommandError("Nothing to run")

        if script.startswith("@"):
            script = script[1:]
            return remote_exec(
                ssh_host=ssh_host,
                session=session,
                project=project,
                script=f'{script} {" ".join(additional_args)}',
                use_screen=use_screen,
            )

        if not os.path.exists(script):
            raise CommandError(f"{script} does not exists")

        script = os.path.abspath(script)
        if not context:
            context = os.path.dirname(script)

        remote_script = os.path.relpath(script, context)
        if remote_script.startswith("../"):
            raise CommandError("Script must be within context directory")

        remote_context = f"/home/{project.config.ssh_user}/opx-{session}"
        shell(
            (
                "rsync",
                "-rzue",
                f"ssh -i {project.config.ssh_key}",
                "--progress",
                f'{context.rstrip("/")}/',
                f"{project.config.ssh_user}@{ssh_host}:{remote_context}",
            )
        )

        if sync_only:
            return

        script = (
            f"cd {shlex.quote(remote_context)} && "
            f"chmod +x {shlex.quote(remote_script)} && "
            f'./{shlex.quote(remote_script)} {" ".join(map(shlex.quote, additional_args))}'
        ).strip()
        init_cmd = environment.context["RUN_INIT_CMD"]
        if init_cmd:
            script = f"{init_cmd} && {script}"

        script = f'bash -c "{script}"'
        shell_cmd = f"screen -L -S {session}" if use_screen else ""

        start_time = time.time()
        shell(
            (
                "ssh",
                "-ti",
                project.config.ssh_key,
                f"{project.config.ssh_user}@{ssh_host}",
                f"cd {shlex.quote(remote_context)}; {shell_cmd} {script}",
            )
        )

        if use_screen:
            elapsed_time = time.time() - start_time
            if elapsed_time < 5:
                logger.info("Screen session closed too soon. Retrieving logs...")
                shell(
                    (
                        "ssh",
                        "-ti",
                        project.config.ssh_key,
                        f"{project.config.ssh_user}@{ssh_host}",
                        f"less +G {shlex.quote(remote_context)}/screenlog.*",
                    )
                )
            else:
                logger.info(
                    "Screen session closed. To check logs:\n"
                    f'  strong-opx run {instance.hostname} "@less +G {shlex.quote(remote_context)}/screenlog.0" --no-screen'
                )
