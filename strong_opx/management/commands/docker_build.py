import argparse
import logging
import os
from typing import Any, Optional

from strong_opx.exceptions import CommandError
from strong_opx.management.command import ProjectCommand
from strong_opx.project import Environment, Project
from strong_opx.providers.docker_registry import DEFAULT_DOCKER_TAG, AbstractDockerRegistry, current_docker_registry
from strong_opx.utils.shell import shell, ssh_agent

logger = logging.getLogger(__name__)


def docker_tag_string(value: Optional[str]) -> str:
    value = value and value.strip()
    if not value:
        return DEFAULT_DOCKER_TAG

    return value


def get_ecr_tags_to_apply(
    registry: "AbstractDockerRegistry",
    environment: "Environment",
    repository_name: str,
    docker_tag: list[str],
) -> tuple[str, set[str]]:
    repository_uri = registry.get_or_create_repository_uri(repository_name)

    revision = registry.get_latest_revision(repository_name)
    image_tag = registry.tag_from_revision(revision + 1)

    tags = {
        f"{repository_uri}:{image_tag}",
        f"{repository_uri}:{DEFAULT_DOCKER_TAG}",
        f"{repository_uri}:{environment.name}-{DEFAULT_DOCKER_TAG}",
    }
    for tag in docker_tag:
        tags.add(f"{repository_uri}:{tag}")

    return repository_uri, tags


def docker_build(
    project: Project, tags: set[str], path: str, additional_args: tuple[str, ...], mount_ssh: bool = False
) -> None:
    cmd = [project.config.docker_executable, "buildx", "build"]
    for tag in sorted(tags):
        cmd.append("-t")
        cmd.append(tag)

    if mount_ssh:
        cmd.append("--ssh")
        cmd.append("default")

    cmd.extend(additional_args)
    cmd.append(path)
    shell(cmd)


class Command(ProjectCommand):
    allow_additional_args = True

    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument("path", help="Docker build context")
        parser.add_argument("--name", help="Image name. Default: directory name")
        parser.add_argument(
            "--ssh",
            dest="mount_ssh",
            action="store_true",
            default=False,
            help="Run ssh-agent and add ssh key to the build context",
        )
        parser.add_argument(
            "--ssh-key",
            dest="ssh_key",
            help="When --ssh is used, use this key instead of the default",
        )
        parser.add_argument(
            "--push",
            dest="docker_push",
            action="store_true",
            default=False,
            help="Push built image to ECR",
        )
        parser.add_argument(
            "--build-arg",
            dest="build_args",
            nargs="+",
            help="Additional build args to docker-build (values will be auto-resolved from stored vars)",
        )
        parser.add_argument(
            "--tag",
            dest="docker_tags",
            type=docker_tag_string,
            nargs="+",
            default=[],
            help=f"Additional tags to apply. {DEFAULT_DOCKER_TAG} tag will always be included",
        )
        super().add_arguments(parser)

    def handle(
        self,
        path: str,
        project: Project,
        environment: Environment,
        additional_args: tuple[str, ...],
        docker_tags: list[str],
        mount_ssh: bool = False,
        ssh_key: Optional[str] = None,
        docker_push: bool = False,
        name: Optional[str] = None,
        build_args: list[str] = None,
        **options: Any,
    ):
        registry = current_docker_registry(environment)
        if registry is None:
            raise CommandError("No container registry configured for current provider")

        if not os.path.isabs(path):
            if os.path.exists(os.path.abspath(path)):
                path = os.path.abspath(path)
            else:
                path = os.path.join(environment.project.path, path)

        if not os.path.exists(path):
            raise CommandError(f"Specified path does not exists: {path}")

        if name is None:
            name = os.path.basename(path)

        if build_args:
            args = []
            for k, v in environment.context.require(*build_args).items():
                args.append("--build-arg")
                args.append(f"{k}={v}")

            additional_args += tuple(args)

        if docker_push:
            registry.login()
            repository_uri, tags = get_ecr_tags_to_apply(registry, environment, name, docker_tags)
            additional_args += (
                "--push",
                "--cache-to",
                "type=inline",
                "--cache-from",
                f"{repository_uri}:{DEFAULT_DOCKER_TAG}",
            )
        else:
            tags = {f"{name}:{tag}" for tag in docker_tags}
            tags.add(f"{name}:{DEFAULT_DOCKER_TAG}")

        if mount_ssh:
            with ssh_agent(ssh_key or project.config.git_ssh_key):
                docker_build(project, tags, path, additional_args, mount_ssh=True)
        else:
            docker_build(project, tags, path, additional_args)
