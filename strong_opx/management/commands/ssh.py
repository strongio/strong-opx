from typing import Any

from strong_opx.management.command import ConnectCommand
from strong_opx.utils.shell import shell


class Command(ConnectCommand):
    help_text = "SSH into private host inside a project/environment"
    allow_additional_args = True
    examples = [
        "strong-opx ssh --project <project> --env <env> 10.0.0.1 ...",
        "strong-opx ssh --project <project> --env <env> primary ...",
        "strong-opx ssh --project <project> --env <env> primary:2 ...",
    ]

    def shell(self, args: list[str], options: dict[str, Any]) -> None:
        shell("ssh " + " ".join(args), shell=True)
