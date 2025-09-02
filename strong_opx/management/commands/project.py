import argparse
import os
from typing import Any

from strong_opx.codegen.project_generator import ProjectGenerator
from strong_opx.config import PROJECT_CONFIG_FILE, system_config
from strong_opx.exceptions import CommandError
from strong_opx.management.command import BaseCommand
from strong_opx.management.utils import select_environment, select_project, validate_project_name
from strong_opx.project import Project


class Command(BaseCommand):
    help_text = "Manage Strong OpX projects"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(title="operation", description="Operation to execute")

        list_ = subparsers.add_parser("list", help="List all registered projects")
        list_.set_defaults(operation="list")

        register = subparsers.add_parser("register", help="Register an existing project")
        register.add_argument("path", help="Root of project")
        register.set_defaults(operation="register")

        unregister = subparsers.add_parser("unregister", help="Remove a registered project")
        unregister.add_argument("project_name", help="Name of project e.g. my-project", type=validate_project_name)
        unregister.set_defaults(operation="unregister")

        create = subparsers.add_parser(
            "create",
            help="Create an empty Strong OpX project",
        )
        create.add_argument("project_name", help="Name of project e.g. my-project")
        create.add_argument("--path", help="Location where to create project, defaults to current directory")
        create.add_argument("--aws-region", help="AWS Region Name. Defaults to us-east-1", default="us-east-1")
        create.set_defaults(operation="create")

        init = subparsers.add_parser(
            "init",
            help="Initialize Strong OpX project. This will create S3 bucket required for deployment.",
        )
        init.add_argument("--project", type=validate_project_name, help="Name of project e.g. my-project")
        init.set_defaults(operation="init")

        init = subparsers.add_parser(
            "init-env",
            help="Initialize Strong OpX Environment. This will create DynamoDB table required for terraform locks.",
        )
        init.add_argument("--project", type=validate_project_name, help="Name of project e.g. my-project")
        init.add_argument("--env", help="Name of Environment e.g. production")
        init.set_defaults(operation="init-env")

    def handle(self, operation=None, **options: Any):
        if operation is None:
            raise CommandError("Specify operation to execute. See --help for more info")

        if operation == "register":
            path = os.path.abspath(options["path"])
            project = Project.from_config(os.path.join(path, PROJECT_CONFIG_FILE))
            system_config.register_project(project.name, path)

        elif operation == "unregister":
            system_config.unregister_project(options["project_name"])

        elif operation == "list":
            for project in system_config.registered_projects:
                print(project, system_config.get_project_path(project), sep="\t")

        elif operation == "create":
            name = options["project_name"]
            full_path = os.path.join(os.path.abspath(options.get("path") or "."), name)

            ProjectGenerator(name, full_path).generate()
            system_config.register_project(name, full_path)

        elif operation == "init":
            select_project(options.get("project")).init()

        elif operation == "init-env":
            project = select_project(options.get("project"))
            select_environment(project, options.get("env")).init()
