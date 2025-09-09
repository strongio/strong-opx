import os
from typing import TYPE_CHECKING

from strong_opx.exceptions import ImproperlyConfiguredError
from strong_opx.hcl.runner import HCLRunner

if TYPE_CHECKING:
    from strong_opx.project import Environment


class TerraformRunner(HCLRunner):
    extension = ".tf"
    env_var_prefix = "TF_VAR"

    def get_executable(self) -> str:
        return self.environment.project.config.terraform_executable


def run_terraform(environment: "Environment", command: str, *additional_args: str):
    project = environment.project

    backend_files = list(
        os.path.join(environment.path, file) for file in os.listdir(environment.path) if file.endswith(".tfbackend")
    )

    if len(backend_files) == 0:
        raise ImproperlyConfiguredError(
            "No backend configuration file found. Please create a .tfbackend file in the environment directory."
        )
    elif len(backend_files) > 1:
        raise ImproperlyConfiguredError(
            "Multiple backend configuration files found. Please ensure there is only one "
            ".tfbackend file in the environment directory."
        )

    environ = dict(os.environ)
    terraform_dir = os.path.join(project.path, "terraform")

    # By default, Terraform creates the .terraform directory in the same directory
    # as the other .tf files. Using TF_DATA_DIR lets us create the .terraform dir
    # wherever we want.
    # Source: https://www.terraform.io/cli/config/environment-variables#tf_data_dir
    terraform_data_dir = os.path.join(environment.path, ".terraform")
    environ["TF_DATA_DIR"] = terraform_data_dir

    if command == "init":
        additional_args += (f"-backend-config={backend_files[0]}",)

    # check to see if .terraform has been created
    elif not os.path.exists(terraform_data_dir):
        raise ImproperlyConfiguredError(
            "Please run `strong-opx terraform init` prior to running other Terraform commands."
        )

    runner = TerraformRunner(environment=environment, directory=terraform_dir)
    runner.run(command, env=environ, additional_args=additional_args)
