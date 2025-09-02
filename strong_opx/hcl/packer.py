import os
import subprocess
from typing import TYPE_CHECKING

from strong_opx.hcl.runner import HCLRunner

if TYPE_CHECKING:
    from strong_opx.project import Environment


class PackerRunner(HCLRunner):
    extension = ".pkr.hcl"
    env_var_prefix = "PKR_VAR"

    def get_executable(self) -> str:
        return self.environment.project.config.packer_executable

    def _run(self, args: tuple[str, ...], env: dict[str, str], **kwargs) -> subprocess.CompletedProcess:
        env["PKR_PLUGIN_PATH"] = os.path.join(self.environment.project.path, ".packer")
        return super()._run(args, env, **kwargs)


def run_packer(environment: "Environment", command: str, *additional_args: str):
    runner = PackerRunner(environment=environment, directory=os.path.join(environment.project.path, "packer"))
    runner.run(command, additional_args=additional_args)
