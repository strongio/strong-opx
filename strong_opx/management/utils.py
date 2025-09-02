import os
from argparse import ArgumentTypeError
from typing import Generator, Optional

from strong_opx.config import PROJECT_CONFIG_FILE, system_config
from strong_opx.exceptions import CommandError
from strong_opx.project import Environment, Project
from strong_opx.utils.prompt import select_prompt


def validate_project_name(value: str) -> str:
    registered_projects = system_config.registered_projects
    if value not in registered_projects:
        raise ArgumentTypeError(f'Unknown project: {value}, Registered projects: {", ".join(registered_projects)}')

    return value


def select_project(project_name: str) -> Project:
    if not project_name:
        project = get_current_project()
        if project:
            return project

    if not project_name:
        project_name = os.getenv("STRONG_OPX_PROJECT")

    if not project_name:
        project_name = select_prompt("Select Project", sorted(system_config.registered_projects))

    return Project.from_name(project_name)


def select_environment(project: Project, environment_name: str) -> Environment:
    if environment_name is None:
        if not project.environments:
            raise CommandError("Project has no environment")
        if len(project.environments) == 1:
            environment_name = project.environments[0]
        else:
            environment_name = os.getenv("STRONG_OPX_ENVIRONMENT")

        if not environment_name:
            environment_name = select_prompt("Select Environment", sorted(project.environments))

    return project.select_environment(name=environment_name)


def walk_to_root() -> Generator[str, None, None]:
    current_dir = os.path.abspath(os.getcwd())

    last_dir = None
    while last_dir != current_dir:
        yield current_dir
        parent_dir = os.path.abspath(os.path.join(current_dir, os.path.pardir))
        last_dir, current_dir = current_dir, parent_dir


def find_project_config_path() -> Optional[str]:
    for directory_path in walk_to_root():
        project_config = os.path.join(directory_path, PROJECT_CONFIG_FILE)
        if os.path.exists(project_config) and os.path.isfile(project_config):
            return project_config


def get_current_project() -> Optional[Project]:
    project_config_path = find_project_config_path()
    if not project_config_path:
        return

    project = Project.from_config(project_config_path)
    if project.name not in system_config.registered_projects:
        raise CommandError(f"Current directory holds project {project.name} that is unknown to registry")

    expected_project_path = system_config.get_project_path(project.name)
    if expected_project_path != os.path.dirname(project_config_path):
        raise CommandError(
            f"Current directory holds project {project.name} "
            f"but another project in different location is registered by that name"
        )

    return project
