import argparse
import logging
import os
import sys
from typing import Any

from colorama import Style

from strong_opx.exceptions import CommandError
from strong_opx.management.utils import select_environment, select_project, validate_project_name
from strong_opx.platforms import GenericPlatform
from strong_opx.project import Environment, Project
from strong_opx.providers import current_provider_error_handler

root_logger = logging.getLogger("strong_opx")
root_logger.propagate = False
root_logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter(
        f"{Style.DIM}%(asctime)s / %(levelname)s:{Style.RESET_ALL} %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
root_logger.addHandler(stream_handler)

logger = logging.getLogger(__name__)


def handle_command_error(e: Exception) -> None:
    if isinstance(e, CommandError):
        print(f"{e.__class__.__name__}: {e}", file=sys.stderr)
        exit(1)

    try:
        current_provider_error_handler(e)
    except CommandError as e2:
        handle_command_error(e2)


class BaseCommand:
    help_text = None
    examples = []
    allow_additional_args = False
    parse_known_args = False

    def create_parser(self, program: str = None, **kwargs: str) -> argparse.ArgumentParser:
        """
        Create and return the ``ArgumentParser`` which will be used to
        parse the arguments to this command.
        """
        epilog = ""
        help_text = self.help_text or (type(self).__doc__ or "").strip()
        if self.examples and program:
            epilog = "Examples:\n   $ {}".format("\n   $ ".join(self.examples))

        parser = argparse.ArgumentParser(
            prog=program,
            description=help_text,
            epilog=epilog,
            argument_default=argparse.SUPPRESS,
            formatter_class=type(
                "HelpFormatter", (argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter), {}
            ),
            **kwargs,
        )
        self.add_arguments(parser)
        parser.add_argument(
            "-v",
            "--verbosity",
            default=2,
            type=int,
            choices=[0, 1, 2, 3],
            help="Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output.",
        )
        parser.add_argument(
            "--traceback", action="store_true", default=False, help="Raise instead of handling known exceptions"
        )
        return parser

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Entry point for subclassed commands to add custom arguments.
        """
        pass

    def run_from_argv(self, argv: list[str]) -> None:
        parser = self.create_parser(f"{os.path.basename(argv[0])} {argv[1]}")

        additional_args = None
        if self.allow_additional_args:
            try:
                i = argv.index("--")
                additional_args = tuple(argv[i + 1 :])
                argv = argv[:i]
            except ValueError:
                additional_args = ()

        if self.parse_known_args and self.allow_additional_args:
            options, pre_additional_args = parser.parse_known_args(argv[2:])
            additional_args = tuple(pre_additional_args) + additional_args
        elif self.parse_known_args:
            options, additional_args = parser.parse_known_args(argv[2:])
            additional_args = tuple(additional_args)
        else:
            options = parser.parse_args(argv[2:])

        if options.verbosity is not None:
            root_logger.setLevel((4 - options.verbosity) * 10)

        if options.traceback:
            self.handle(**self.transform_args(options, additional_args))
        else:
            try:
                self.handle(**self.transform_args(options, additional_args))
            except Exception as e:
                handle_command_error(e)

    def transform_args(self, options: argparse.Namespace, additional_args: tuple[str, ...]) -> dict[str, Any]:
        options = vars(options)
        if additional_args is not None:
            options["additional_args"] = additional_args

        return options

    def handle(self, **options: Any) -> None:
        raise NotImplementedError()


class ProjectCommand(BaseCommand):
    require_environment = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--project",
            type=validate_project_name,
            help=(
                "Select project by its name. If missing, strong-opx will attempt to auto-select project based "
                "on current working directory and its parents and looking for presence of configured project"
            ),
        )
        parser.add_argument(
            "--env",
            dest="environment",
            help="Environment name. If project has only one environment that will be auto selected",
        )

    def transform_args(self, options: argparse.Namespace, additional_args: tuple[str, ...]) -> dict[str, Any]:
        options = super().transform_args(options, additional_args)
        project = options["project"] = select_project(options.get("project"))

        if self.require_environment:
            environment = options["environment"] = select_environment(project, options.get("environment"))
        else:
            environment = options.get("environment")
            if environment:
                options["environment"] = project.select_environment(environment)

        if environment:
            print(f"Using Project: {Style.BRIGHT}{project.name} [{environment.name}]{Style.RESET_ALL}")
        else:
            print(f"Using Project: {Style.BRIGHT}{project.name}{Style.RESET_ALL}")

        return options


class ConnectCommand(ProjectCommand):
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("hostname", help="Hostname or host group or ip of instance")

    def handle(
        self,
        environment: Environment,
        project: Project,
        hostname: str,
        **options: Any,
    ) -> None:
        platform = environment.select_platform(GenericPlatform)

        instance = platform.resolve_instance(hostname)[0]
        ssh_host = platform.get_ssh_host(instance)
        args = ["-i", project.config.ssh_key, f"{project.config.ssh_user}@{ssh_host}"]

        ssh_proxy_command = platform.ssh_proxy_command(instance.hostname)
        if ssh_proxy_command:
            args.append("-o")
            args.append(f"ProxyCommand='{ssh_proxy_command}'")

        if options.get("additional_args"):
            args = args + list(options["additional_args"])

        self.shell(args, options)

    def shell(self, args: list[str], options: dict[str, Any]) -> None:
        raise NotImplementedError()
