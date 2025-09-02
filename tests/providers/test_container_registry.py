import json
from unittest import TestCase
from unittest.mock import patch

import boto3
from parameterized import parameterized

from strong_opx.exceptions import RepositoryNotFoundException
from strong_opx.providers.container_registry import AbstractContainerRegistry
from tests.mocks import create_mock_environment, create_mock_project


class ContainerRegistryTests(TestCase):
    def setUp(self) -> None:
        self.project = create_mock_project()
        self.environment = create_mock_environment(project=self.project)

    @parameterized.expand(
        [
            ("unittest-1", 1),
            ("unittest-1.b80886c", 1),
            ("unittest-100", 100),
            ("other-100", 0),
            ("unitest-latest", 0),
            ("unitest-latest.b80886c", 0),
            ("cuda-3.8", 0),
        ]
    )
    def test_revision_from_tag(self, tag: str, expected_revision: int):
        revision = AbstractContainerRegistry(self.environment).revision_from_tag(tag)
        self.assertEqual(revision, expected_revision)

    @parameterized.expand(
        [
            (1, None, "unittest-1"),
            (2, "b80886c", "unittest-2.b80886c"),
        ]
    )
    def test_tag_from_revision(self, revision, postfix, expected_tag):
        self.environment.project.git_revision_hash.return_value = postfix
        tag = AbstractContainerRegistry(self.environment).tag_from_revision(revision)
        self.assertEqual(tag, expected_tag)

    @patch.object(AbstractContainerRegistry, "get_repository_uri")
    @patch.object(AbstractContainerRegistry, "create_repository")
    def test_get_or_create_repository_uri__not_found(self, mock_create_repository, mock_get_repository_uri):
        mock_get_repository_uri.side_effect = RepositoryNotFoundException

        AbstractContainerRegistry(self.environment).get_or_create_repository_uri("unknown-repo")
        mock_get_repository_uri.assert_called_once_with("unknown-repo")
        mock_create_repository.assert_called_once_with("unknown-repo")

    @patch.object(AbstractContainerRegistry, "get_repository_uri")
    def test_get_or_create_repository_uri__exists(self, mock_get_repository_uri):
        mock_get_repository_uri.return_value = "some-repo-uri"

        uri = AbstractContainerRegistry(self.environment).get_or_create_repository_uri("some-repo")
        self.assertEqual(uri, "some-repo-uri")

    @patch.object(AbstractContainerRegistry, "iter_image_tags")
    def test_get_latest_revision__not_found(self, mock_iter_image_tags):
        mock_iter_image_tags.return_value = []

        revision = AbstractContainerRegistry(self.environment).get_latest_revision("unknown-repo")
        self.assertEqual(revision, 0)

    @patch.object(AbstractContainerRegistry, "iter_image_tags")
    def test_get_latest_revision(self, mock_iter_image_tags):
        mock_iter_image_tags.return_value = ["unittest-1", "unittest-2"]

        revision = AbstractContainerRegistry(self.environment).get_latest_revision("some-repo")
        self.assertEqual(revision, 2)

    @patch.object(AbstractContainerRegistry, "iter_image_tags")
    @patch.object(AbstractContainerRegistry, "get_repository_uri")
    def test_get_latest_image_uri(self, mock_get_repository_uri, mock_iter_image_tags):
        mock_iter_image_tags.return_value = ["unittest-10"]
        mock_get_repository_uri.return_value = "some-repo-uri"

        image_uri = AbstractContainerRegistry(self.environment).get_latest_image_uri("some-repo")
        self.assertEqual(image_uri, "some-repo-uri:unittest-10")

    @patch.object(AbstractContainerRegistry, "iter_image_tags")
    @patch.object(AbstractContainerRegistry, "get_repository_uri")
    def test_get_latest_image_uri__not_found(self, mock_get_repository_uri, mock_iter_image_tags):
        mock_iter_image_tags.return_value = []
        mock_get_repository_uri.side_effect = RepositoryNotFoundException

        registry = AbstractContainerRegistry(self.environment)

        image_uri = registry.get_latest_image_uri("some-repo")
        self.assertEqual(image_uri, "some-repo:latest")
