import logging
from functools import cached_property
from typing import TYPE_CHECKING, Generator, Optional

from google.api_core.exceptions import NotFound
from google.cloud.artifactregistry_v1 import (
    ArtifactRegistryClient,
    CleanupPolicy,
    CleanupPolicyMostRecentVersions,
    CreateRepositoryRequest,
    ListVersionsRequest,
    Repository,
    VersionView,
)

from strong_opx.exceptions import ProcessError, RepositoryNotFoundException
from strong_opx.providers.discovery import current_provider
from strong_opx.providers.docker_registry import AbstractDockerRegistry
from strong_opx.utils.shell import shell

if TYPE_CHECKING:
    from strong_opx.providers.gcloud.provider import GCloudProvider

logger = logging.getLogger(__name__)


def parse_repository_name(name: str) -> tuple[str, str]:
    parts = name.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid repository name: {name}. It should be of format: <repository-name>/<package-name>")

    return parts[0], parts[1]


class DockerRegistry(AbstractDockerRegistry):
    @cached_property
    def provider(self) -> "GCloudProvider":
        provider: "GCloudProvider" = current_provider()  # type: ignore[assignment]
        return provider

    @cached_property
    def client(self):
        return ArtifactRegistryClient()

    def login(self):
        shell(
            [
                "gcloud",
                "auth",
                "configure-docker",
                "--quiet",
                f"{self.provider.config.compute_region}-docker.pkg.dev",
            ]
        )

    def create_repository(self, full_repository_name: str) -> str:
        repository_name, package_name = parse_repository_name(full_repository_name)
        logger.info(f"Creating Artifact repository: {repository_name}...")

        request = CreateRepositoryRequest(
            parent=self.provider.gcp_project_path,
            repository_id=repository_name,
            repository=Repository(
                format_=Repository.Format.DOCKER,
                labels={"provisioned-by": "strong-opx"},
                cleanup_policies={
                    "keep-recent-versions": CleanupPolicy(
                        action=CleanupPolicy.Action.KEEP,
                        most_recent_versions=CleanupPolicyMostRecentVersions(
                            keep_count=self.max_images_to_keep,
                        ),
                    )
                },
            ),
        )

        self.client.create_repository(request=request)
        return self._repository_uri(repository_name, package_name)

    def get_repository_uri(self, full_repository_name: str) -> Optional[str]:
        repository_name, package_name = parse_repository_name(full_repository_name)

        repo_path = "/".join([self.provider.gcp_project_path, f"repositories/{repository_name}"])

        try:
            repository = self.client.get_repository(name=repo_path)
            if repository.format_ != Repository.Format.DOCKER:
                raise ProcessError(f"Repository {repository_name} is not a Docker repository.")
        except NotFound:
            raise RepositoryNotFoundException()

        return self._repository_uri(repository_name, package_name)

    def _repository_uri(self, repository_name: str, package_name: str) -> str:
        config = self.provider.config
        return "/".join(
            [
                f"{config.compute_region}-docker.pkg.dev",
                config.project,
                repository_name,
                package_name,
            ]
        )

    def iter_image_tags(self, full_repository_name: str) -> Generator[str, None, None]:
        repository_name, package_name = parse_repository_name(full_repository_name)
        package_path = "/".join(
            [
                self.provider.gcp_project_path,
                f"repositories/{repository_name}",
                f"packages/{package_name}",
            ]
        )

        request = ListVersionsRequest(parent=package_path, page_size=100, view=VersionView.FULL)

        try:
            versions = self.client.list_versions(request=request)
            for version in versions:
                for tag in version.related_tags:
                    yield tag.name.rsplit("/", 1)[1]

        except NotFound:
            pass
