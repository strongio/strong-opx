import os
from textwrap import TextWrapper
from typing import Generator, Union

from colorama import Fore, Style

from strong_opx.utils.tracking import Position, get_position


class CommandError(Exception):
    pass


class RepositoryNotFoundException(Exception):
    pass


class ComputeInstanceError(ValueError, CommandError):
    pass


class ImproperlyConfiguredError(CommandError):
    pass


class ProjectError(CommandError):
    pass


class ProjectEnvironmentError(ProjectError):
    pass


class ProcessError(CommandError):
    pass


class HelmError(CommandError):
    pass


class PluginError(CommandError):
    pass


class VaultError(CommandError):
    pass


class ErrorDetail:
    lines_for_context = 2
    __slots__ = ("error", "file_path", "start_pos", "end_pos", "hint")

    def __init__(
        self,
        error: str,
        file_path: str = None,
        start_pos: Position = None,
        end_pos: Position = None,
        hint: str = None,
    ):
        self.error = error
        self.file_path = file_path
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.hint = hint

    def read_block(self, file_path: str) -> Generator[str, None, None]:
        def read_lines(start_index: int, end_index: int) -> Generator[str, None, None]:
            with open(file_path) as f:
                for _ in range(start_index - 1):
                    f.readline()

                last_line = f.readline()
                for _ in range(end_index - start_index):
                    yield last_line.rstrip()
                    last_line = f.readline()

                yield last_line.rstrip()

        lines = []

        start_line = max(1, self.start_pos.line - self.lines_for_context)
        end_line = (self.end_pos.line if self.end_pos else self.start_pos.line) + self.lines_for_context
        before_context_lines = self.start_pos.line - start_line
        n_problem_lines = (self.end_pos.line if self.end_pos else self.start_pos.line) - self.start_pos.line + 1

        lines_reader = read_lines(start_line, end_line)

        for _ in range(before_context_lines):
            line = next(lines_reader)
            if not line:
                start_line += len(lines) + 1
                lines = []
            else:
                lines.append(line)

        for _ in range(n_problem_lines):
            lines.append(next(lines_reader))

        ln_content = lines[-1]
        if self.end_pos and self.end_pos.column:
            lines[-1] = f"{ln_content[:self.end_pos.column - 1]}{Style.RESET_ALL}{ln_content[self.end_pos.column - 1:]}"
        else:
            lines[-1] += Style.RESET_ALL

        l1_content = lines[-n_problem_lines]
        if self.start_pos.column:
            lines[-n_problem_lines] = (
                f"{l1_content[:self.start_pos.column - 1]}{Style.BRIGHT}" f"{l1_content[self.start_pos.column - 1:]}"
            )

        for _ in range(self.lines_for_context):
            line = next(lines_reader)
            if not line:
                # Exhaust iterator
                list(lines_reader)
                break

            lines.append(line)

        for n, line in enumerate(lines, start_line):
            yield f"{Style.DIM}{n}:  {Style.RESET_ALL}{line}"

    def __str__(self):
        lines = self.error.splitlines()
        lines[0] = f"{Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}{lines[0]}"
        lines[-1] += Style.RESET_ALL

        if self.file_path:
            from strong_opx.project import Project

            if Project.current():
                project_path = Project.current().path
            else:
                project_path = "."

            if os.path.isabs(self.file_path):
                display_path = os.path.relpath(self.file_path, project_path)
                file_path = self.file_path
            else:
                display_path = self.file_path
                file_path = os.path.join(project_path, self.file_path)

            # If file is from outside of project repo, don't show relative path
            if display_path[0] == ".":
                display_path = os.path.abspath(display_path)

            position_line = f"  in {display_path}"
            if self.start_pos:
                position_line += f" on line {self.start_pos.line}"
                if self.start_pos.column:
                    position_line += f" column {self.start_pos.column}"

            lines.append("")
            lines.append(position_line)

            if self.start_pos:
                for line in self.read_block(file_path):
                    lines.append(f"  {line}")

        if self.hint:
            lines.append("")
            for line in self.hint.splitlines():
                if line:
                    lines.extend(TextWrapper(width=80, replace_whitespace=False).wrap(line))
                else:  # Keep empty newlines
                    lines.append("")

        if len(lines) > 1:
            for i in range(len(lines)):
                lines[i] = f"{Fore.RED}│{Fore.RESET} {lines[i]}"

            lines.insert(0, f"{Fore.RED}╷{Fore.RESET}")
            lines.append(f"{Fore.RED}╵{Fore.RESET}")

        return "\n".join(lines)


class ConfigurationError(CommandError):
    __slots__ = ("errors",)

    def __init__(self, error: Union[str, ErrorDetail, list[ErrorDetail]], **kwargs):
        if isinstance(error, list):
            self.errors = error
        elif isinstance(error, ErrorDetail):
            self.errors = [error]
        else:
            self.errors = [ErrorDetail(error=error, **kwargs)]

    def __str__(self):
        lines = "\n".join(map(str, self.errors)).splitlines()
        if len(lines) > 1:
            lines.insert(0, "")

        return "\n".join(lines)


class YAMLError(ConfigurationError):
    pass


class VariableError(ConfigurationError):
    def __init__(self, message: str, var_name: str):
        self.var_name = var_name
        file_path, start_pos, end_pos = get_position(var_name)
        super().__init__(message, file_path=file_path, start_pos=start_pos, end_pos=end_pos)


class UndefinedVariableError(ConfigurationError):
    def __init__(self, *names: str):
        self.names = names

        errors = []
        for name in sorted(names):
            errors.append(ErrorDetail(f"{name} is undefined", *get_position(name)))

        super().__init__(errors)


class TemplateError(ConfigurationError):
    def __init__(self, error: str, file_name: str, **kwargs):
        super().__init__([ErrorDetail(error=error, file_path=file_name, **kwargs)])
