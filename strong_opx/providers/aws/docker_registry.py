import json
import logging
from functools import cached_property
from typing import Any, Generator, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from strong_opx.project import Project
from strong_opx.providers.aws.config import get_aws_config
from strong_opx.providers.aws.errors import handle_boto_error
from strong_opx.providers.aws.iam import get_current_account_id
from strong_opx.providers.docker_registry import AbstractDockerRegistry
from strong_opx.utils.shell import shell

logger = logging.getLogger(__name__)


class DockerRegistry(AbstractDockerRegistry):
    @cached_property
    def client(self):
        return boto3.client("ecr")

    def login(self):
        account_id = get_current_account_id()
        region = get_aws_config("region")

        docker_executable = Project.current().config.docker_executable

        shell(
            f"aws ecr get-login-password --region {region} | "
            f"{docker_executable} login --username AWS --password-stdin "
            f"{account_id}.dkr.ecr.{region}.amazonaws.com",
            shell=True,
        )

    def create_repository(self, repository_name: str) -> dict[str, Any]:
        logger.info(f"Creating ECR repository: {repository_name}...")
        response = self.client.create_repository(repositoryName=repository_name)
        self.client.put_lifecycle_policy(
            repositoryName=repository_name,
            lifecyclePolicyText=json.dumps(
                {
                    "rules": [
                        {
                            "rulePriority": 1,
                            "description": f"Only keep {self.max_images_to_keep} images for {self.environment.name}",
                            "selection": {
                                "tagStatus": "tagged",
                                "tagPrefixList": [f"{self.environment.name}-"],
                                "countType": "imageCountMoreThan",
                                "countNumber": self.max_images_to_keep,
                            },
                            "action": {"type": "expire"},
                        }
                    ]
                }
            ),
        )

        return response["repository"]["repositoryUri"]

    def get_repository_uri(self, repository_name: str) -> Optional[str]:
        try:
            response = self.client.describe_repositories(repositoryNames=[repository_name])
        except (ClientError, NoCredentialsError) as e:
            handle_boto_error(e)
        else:
            return response["repositories"][0]["repositoryUri"]

    def iter_image_tags(self, repository_name: str) -> Generator[str, None, None]:
        try:
            paginator = self.client.get_paginator("describe_images")
            for page in paginator.paginate(repositoryName=repository_name):
                for image in page["imageDetails"]:
                    for tag in image.get("imageTags", []):
                        yield tag
        except (ClientError, NoCredentialsError) as e:
            handle_boto_error(e, ignore=("RepositoryNotFoundException",))
