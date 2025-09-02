import argparse
import importlib.util
import os
import pkgutil
import sys
from difflib import SequenceMatcher
from typing import Generator

import colorama

from strong_opx import __version__
from strong_opx.management.utils import validate_project_name

colorama.init()

COMMAND_ALIAS = {
    "g": "generate",
}


def _command_name_from_module_name(module_name: str) -> str:
    return module_name.rsplit(".", 1)[-1].replace("_", ":")


def _list_commands() -> Generator[str, None, None]:
    from strong_opx.management import commands

    for _, module_name, _ in pkgutil.iter_modules(commands.__path__):
        yield _command_name_from_module_name(module_name)


def _list_similar_commands(user_command: str) -> list[str]:
    similarity = {}

    for known_command in _list_commands():
        ratio = SequenceMatcher(None, known_command, user_command).ratio()
        if ratio > 0.8:
            similarity[known_command] = ratio

    return [x[0] for x in sorted(similarity.items(), key=lambda x: x[1])]


def _validate_command(command: str):
    command = COMMAND_ALIAS.get(command, command)
    module_name = command.replace(":", "_").replace("-", "_")

    try:
        module_spec = importlib.util.find_spec(f"strong_opx.management.commands.{module_name}")
    except ModuleNotFoundError:
        module_spec = None

    if module_spec is None:
        print(f'strong-opx: "{command}" is not a strong-opx command. See strong-opx --help')

        similar_commands = _list_similar_commands(command)
        if similar_commands:
            print("\nThe most similar command(s) are:")
            for command_name in similar_commands:
                print(f"    {command_name}")

            print()

        exit(1)

    return module_spec


def _print_main_help(parser: argparse.ArgumentParser):
    print(f'\nType "{parser.prog} <command> --help" for help on specific command\n')
    print("strong-opx commands:")

    for command_name in _list_commands():
        print(f"    {command_name}")


def main():
    parser = argparse.ArgumentParser(usage="%(prog)s [--help] subcommand [options] [args]", add_help=False)
    parser.add_argument("-h", "--help", action="store_true", help="show this help message and exit")
    parser.add_argument("--version", action="store_true", help="show strong-opx version and exit")
    parser.add_argument("--project", type=validate_project_name, help="Select project by its name.")
    parser.add_argument("--env")
    parser.add_argument(dest="command", nargs="?", help="name of command to execute", type=_validate_command)

    argv = sys.argv[1:]
    try:
        i = argv.index("--")
        additional_args = tuple(argv[i + 1 :])
        argv = argv[:i]
    except ValueError:
        additional_args = None

    args, command_args = parser.parse_known_args(args=argv)
    if additional_args:
        command_args.append("--")
        command_args.extend(additional_args)

    if args.command:
        if args.help:
            command_args.append("--help")
    else:
        if args.help:
            _print_main_help(parser)
        elif args.version:
            print(__version__)
        else:
            parser.error("A subcommand is required, e.g., strong-opx deploy")
            exit(1)

        exit(0)

    if args.env:
        command_args.insert(0, "--env")
        command_args.insert(1, args.env)

    if args.project:
        command_args.insert(0, "--project")
        command_args.insert(1, args.project)

    path_env = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{os.path.dirname(sys.executable)}:{path_env}"

    command_name = _command_name_from_module_name(args.command.name)
    command_module = args.command.loader.load_module()
    command_class = getattr(command_module, "Command", None)

    if command_class is None:
        raise ValueError(f"{args.command.origin} does not define a Command class")

    command = command_class()
    command_args.insert(0, parser.prog)
    command_args.insert(1, command_name)
    command.run_from_argv(command_args)


if __name__ == "__main__":
    main()
