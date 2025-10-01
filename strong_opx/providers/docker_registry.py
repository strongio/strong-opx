import logging
import re
from typing import TYPE_CHECKING, Generator, Optional

from strong_opx.exceptions import RepositoryNotFoundException
from strong_opx.providers.discovery import current_provider_name
from strong_opx.template import Template
from strong_opx.utils.module_loading import import_module_attr_if_exists

if TYPE_CHECKING:
    from strong_opx.project.environment import Environment

logger = logging.getLogger(__name__)
DEFAULT_DOCKER_TAG = "latest"


class AbstractDockerRegistry:
    max_images_to_keep = 8
    revision_tag_re = re.compile(r"^(.+)-([0-9]+)(\.[a-z0-9]+)?$")

    def __init__(self, environment: "Environment"):
        self.environment = environment

    def login(self):
        raise NotImplementedError()

    def create_repository(self, repository_name: str) -> str:
        raise NotImplementedError()

    def get_repository_uri(self, repository_name: str) -> Optional[str]:
        raise NotImplementedError()

    def get_or_create_repository_uri(self, repository_name: str) -> str:
        try:
            return self.get_repository_uri(repository_name)
        except RepositoryNotFoundException:
            return self.create_repository(repository_name)

    def revision_from_tag(self, tag: str) -> int:
        match = self.revision_tag_re.match(tag)
        if match:
            env = match.group(1)
            if env == self.environment.name:
                return int(match.group(2))

        return 0

    def tag_from_revision(self, revision: int) -> str:
        tag = f"{self.environment.name}-{revision}"
        version_hash = self.environment.project.git_revision_hash()

        if version_hash:
            tag = f"{tag}.{version_hash}"

        return tag

    def iter_image_tags(self, repository_name: str) -> Generator[str, None, None]:
        raise NotImplementedError()

    def get_latest_revision(self, repository_name: str) -> int:
        revision = 0

        for tag in self.iter_image_tags(repository_name):
            revision = max(self.revision_from_tag(tag), revision)

        return revision

    def get_latest_image_uri(self, repository_name: str, render_repository_name: bool = False) -> str:
        if render_repository_name:
            repository_name = Template(repository_name).render(self.environment.context)

        revision = 0
        latest_tag = DEFAULT_DOCKER_TAG

        for tag in self.iter_image_tags(repository_name):
            tag_revision = self.revision_from_tag(tag)
            if tag_revision > revision:
                revision = tag_revision
                latest_tag = tag

        try:
            repository_uri = self.get_repository_uri(repository_name)
        except RepositoryNotFoundException:
            repository_uri = repository_name

        return f"{repository_uri}:{latest_tag}"


def current_docker_registry(environment: "Environment") -> Optional[AbstractDockerRegistry]:
    registry_class: Optional[type[AbstractDockerRegistry]] = import_module_attr_if_exists(
        f"strong_opx.providers.{current_provider_name()}.docker_registry",
        "DockerRegistry",
    )
    if registry_class:
        return registry_class(environment)

    return None
