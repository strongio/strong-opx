import argparse
from typing import Any

from strong_opx.exceptions import CommandError
from strong_opx.management.command import ConnectCommand
from strong_opx.utils.shell import shell


def parse_path(path):
    if path[0] == "@":
        return True, path[1:]

    return False, path


class Command(ConnectCommand):
    help_text = "SCP into private host inside a project/environment"
    allow_additional_args = True
    examples = [
        "strong-opx scp --project <project> --env <env> 10.0.0.1 @<remote-path> <local-path>",
        "strong-opx scp --project <project> --env <env> 10.0.0.1 <local-path> @<remote-path>",
        "strong-opx scp --project <project> --env <env> primary @<remote-path> <local-path>",
        "strong-opx scp --project <project> --env <env> primary:2 <remote-path> @<local-path>",
    ]

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("source", help="Source path. To represent server path prepend @")
        parser.add_argument("target", help="Target path. To represent server path prepend @")

    def shell(self, args: list[str], options: dict[str, Any]) -> None:
        source_remote, source_path = parse_path(options["source"])
        target_remote, target_path = parse_path(options["target"])

        if source_remote == target_remote:
            raise CommandError("source and target are referring to remote machine")

        remote_host = args.pop(2)

        if source_remote:
            source_path = f"{remote_host}:{source_path}"

        if target_remote:
            target_path = f"{remote_host}:{target_path}"

        args.append(source_path)
        args.append(target_path)
        shell("scp " + " ".join(args), shell=True)
