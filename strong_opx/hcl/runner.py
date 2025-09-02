import os
import subprocess
from typing import TYPE_CHECKING

from strong_opx.exceptions import UndefinedVariableError
from strong_opx.hcl.extractor import HCLVariableExtractor
from strong_opx.utils.shell import shell

if TYPE_CHECKING:
    from strong_opx.project import Environment


class HCLRunner:
    extension: str
    env_var_prefix: str

    def __init__(self, environment: "Environment", directory: str):
        self.environment = environment
        self.directory = directory

    def extract_vars(self) -> dict[str, str]:
        env_dict = {}
        extractor = HCLVariableExtractor()

        context = self.environment.context

        for filename in os.listdir(self.directory):
            if filename.endswith(self.extension):
                file_path = os.path.join(self.directory, filename)
                with open(file_path) as f:
                    extractor.extract(file_path, f)

        missing_vars = []
        for var in extractor.required_vars:
            if var not in context:
                missing_vars.append(var)
                continue

            env_dict[f"{self.env_var_prefix}_{var}"] = str(context[var])

        if missing_vars:
            raise UndefinedVariableError(*missing_vars)

        for var in extractor.optional_vars:
            if var in context:
                env_dict[f"{self.env_var_prefix}_{var}"] = str(context[var])

        return env_dict

    def get_executable(self) -> str:
        raise NotImplementedError()

    def _run(self, args: tuple[str, ...], env: dict[str, str], **kwargs) -> subprocess.CompletedProcess:
        return shell(args, env=env, cwd=self.directory, **kwargs)

    def run(
        self, command: str, env: dict[str, str] = None, additional_args: tuple[str, ...] = ()
    ) -> subprocess.CompletedProcess:
        if env is None:
            env = dict(os.environ)

        env.update(self.extract_vars())
        args = (self.get_executable(), command, *additional_args)
        return self._run(args, env=env)
