import hashlib
import json
import os
from random import random
from unittest import TestCase, mock

import boto3
from moto import mock_aws

from strong_opx.providers.aws.container_registry import ContainerRegistry
from strong_opx.providers.aws.errors import RepositoryNotFoundException
from tests.mocks import create_mock_environment, create_mock_project


def _create_image_digest(contents=None):
    if not contents:
        contents = f"docker_image{int(random() * 10 ** 6)}"

    return "sha256:%s" % hashlib.sha256(contents.encode("utf-8")).hexdigest()


def _create_image_manifest():
    return {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": 7023,
            "digest": _create_image_digest("config"),
        },
        "layers": [
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 32654,
                "digest": _create_image_digest("layer1"),
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 16724,
                "digest": _create_image_digest("layer2"),
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 73109,
                # randomize image digest
                "digest": _create_image_digest(),
            },
        ],
    }


@mock_aws
@mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-1"})
class ContainerRegistryTests(TestCase):
    def setUp(self) -> None:
        self.project = create_mock_project()
        self.environment = create_mock_environment(project=self.project)

    def test_create_repository_with_revisions(self):
        repository = ContainerRegistry(self.environment).create_repository("unittest-image")
        self.assertEqual(repository["imageTagMutability"], "MUTABLE")
        self.assertEqual(repository["repositoryName"], "unittest-image")

    def test_get_repository_uri__not_found(self):
        with self.assertRaises(RepositoryNotFoundException):
            ContainerRegistry(self.environment).get_repository_uri("unknown-repo")

    def test_get_repository_uri__exists(self):
        registry = ContainerRegistry(self.environment)
        registry.create_repository("some-repo")

        uri = registry.get_repository_uri("some-repo")
        self.assertEqual(uri, "123456789012.dkr.ecr.us-east-1.amazonaws.com/some-repo")

    def test_iter_image_tags(self):
        registry = ContainerRegistry(self.environment)
        registry.create_repository("some-repo")
        boto3.client("ecr").put_image(
            repositoryName="some-repo",
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag="unittest-1",
        )

        boto3.client("ecr").put_image(
            repositoryName="some-repo",
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag="unittest-10",
        )

        image_tags = list(registry.iter_image_tags("some-repo"))
        self.assertListEqual(image_tags, ["unittest-1", "unittest-10"])
