import argparse
import sys
from typing import Any

from strong_opx import yaml
from strong_opx.exceptions import CommandError
from strong_opx.management.command import ProjectCommand
from strong_opx.project import Environment
from strong_opx.vault import VaultCipher


class Command(ProjectCommand):
    help_text = "Environment variables management"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        subparsers = parser.add_subparsers(title="operation", description="Operation to execute")

        encrypt = subparsers.add_parser("encrypt", help="Encrypt value or environment variable")
        encrypt.add_argument("--value", help="Value to encrypt")
        encrypt.add_argument("--vars", nargs="*", help="Variables to encrypt")
        encrypt.set_defaults(operation="encrypt")

        decrypt = subparsers.add_parser("decrypt", help="Decrypt environment variables")
        decrypt.add_argument("--vars", nargs="*", help="If specified, decrypt only these variables.")
        decrypt.set_defaults(operation="decrypt")

    def handle(self, operation=None, **options: Any) -> None:
        if operation is None:
            raise CommandError("Specify operation to execute. See --help for more info")

        if operation == "encrypt":
            self.handle_encrypt(**options)
        elif operation == "decrypt":
            self.handle_decrypt(**options)

    def handle_encrypt(self, environment: Environment, **options: Any):
        if options["vars"]:
            context = environment.context

            for v in options["vars"]:
                cipher = VaultCipher.encrypt(context[v], environment.vault_secret)
                print(f"{v}: !vault |")
                for line in str(cipher).split():
                    print(" ", line)

                print()
        elif options["value"]:
            encrypted = VaultCipher.encrypt(options["value"], environment.vault_secret)
            print(str(encrypted))
        else:
            raise CommandError("Either provide --value or --vars to encrypt")

    def handle_decrypt(self, environment: Environment, **options: Any):
        context = environment.context
        if options.get("vars"):
            for var_name in options["vars"]:
                print(f"{var_name}: {context[var_name]}")
        else:
            yaml.dump(context.as_dict(exclude_initial=True), sys.stdout)
