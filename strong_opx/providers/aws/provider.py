import logging
import os
import sys
from functools import cached_property
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Callable, Collection

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from strong_opx.project import Environment, Project
from strong_opx.providers.aws.compute import describe_instances
from strong_opx.providers.aws.config import AWSConfig, get_aws_config
from strong_opx.providers.aws.context_hooks import import_and_clean_environ_hook, update_environ_hook
from strong_opx.providers.aws.errors import handle_boto_error
from strong_opx.providers.aws.iam import assume_role
from strong_opx.providers.compute import ComputeInstanceDescription
from strong_opx.providers.provider import Provider
from strong_opx.utils.shell import shell

if TYPE_CHECKING:
    from strong_opx.template import Context

logger = logging.getLogger(__name__)


class AWSProvider(Provider):
    config: AWSConfig
    compute_instance_id_re = r"^i-[0-9a-f]+$"

    def get_additional_context_hooks(self) -> tuple[Callable[["Context"], None], ...]:
        return (
            self.update_context,
            import_and_clean_environ_hook,
            update_environ_hook,
        )

    def update_context(self, context: "Context"):
        aws_profile = self.default_aws_profile
        if aws_profile is not None:
            context["AWS_PROFILE"] = aws_profile

        context.update(self.config.dict())

    @cached_property
    def default_aws_profile(self):
        project = Project.current()

        return project.config.get("aws", "aws_profile", fallback=None)

    def init_project(self, project: "Project"):
        session_kwargs = {}
        client_kwargs = {
            "region_name": self.config.region if self.config.region else "us-east-1",
        }

        ops_bucket_name = f"{project.name}-ops"
        aws_profile = self.default_aws_profile
        if aws_profile is not None:
            session_kwargs["profile_name"] = aws_profile

        logger.info(f"Creating S3 bucket: {ops_bucket_name}...")

        s3_client = boto3.Session(**session_kwargs).client("s3", **client_kwargs)
        s3_client.create_bucket(
            ACL="private",
            Bucket=ops_bucket_name,
            ObjectOwnership="BucketOwnerEnforced",
        )
        s3_client.put_bucket_tagging(
            Bucket=ops_bucket_name,
            Tagging={
                "TagSet": [
                    {
                        "Key": "Description",
                        "Value": f"Bucket used by Terraform to store the state of the "
                        f"infrastructure of the {project.name} project",
                    },
                ]
            },
        )

        logger.info(f"Block public access to bucket and its objects...")
        s3_client.put_public_access_block(
            Bucket=ops_bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        logger.info(f"Enabling Versioning on bucket...")
        s3_client.put_bucket_versioning(Bucket=ops_bucket_name, VersioningConfiguration={"Status": "Enabled"})

        logger.info(f"Enabling Server-Side Encryption on bucket...")
        s3_client.put_bucket_encryption(
            Bucket=ops_bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
            },
        )

    def init_environment(self, environment: "Environment") -> None:
        dynamodb_client = boto3.client("dynamodb")
        dynamodb_client.create_table(
            AttributeDefinitions=[
                {"AttributeName": "LockID", "AttributeType": "S"},
            ],
            TableName=f"{environment.project.name}-{environment.name}-terraform-state",
            KeySchema=[
                {"AttributeName": "LockID", "KeyType": "HASH"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            Tags=[
                {
                    "Key": "Description",
                    "Value": (
                        "Table used by Terraform to ensure that only one user is modifying the"
                        f"{environment.name} resources of {environment.project.name} at the same time"
                    ),
                },
                {
                    "Key": "Environment",
                    "Value": environment.name,
                },
                {
                    "Key": "Project",
                    "Value": environment.project.name,
                },
            ],
        )

    def query_compute_instances(self, ip_address: IPv4Address) -> list[ComputeInstanceDescription]:
        return describe_instances(
            Filters=[
                {
                    "Name": (
                        "network-interface.addresses.private-ip-address" if ip_address.is_private else "ip-address"
                    ),
                    "Values": [str(ip_address)],
                }
            ]
        )

    def describe_compute_instance(self, instance_id: str) -> ComputeInstanceDescription:
        instances = describe_instances(InstanceIds=[instance_id])
        if len(instances) == 0:
            raise ValueError(f'Unable to find an instance with ID "{instance_id}"')

        return instances[0]

    def start_compute_instance(self, instance_ids: Collection[str], wait: bool = True) -> None:
        client = boto3.client("ec2")
        client.start_instances(InstanceIds=instance_ids)

        if wait:
            waiter = client.get_waiter("instance_status_ok")
            logger.info(f"Waiting for {len(instance_ids)} instance(s) to start...")
            waiter.wait(InstanceIds=instance_ids)

    def stop_compute_instance(self, instance_ids: Collection[str], wait: bool = True) -> None:
        client = boto3.client("ec2")
        client.stop_instances(InstanceIds=instance_ids)

        if wait:
            waiter = client.get_waiter("instance_stopped")
            logger.info(f"Waiting for {len(instance_ids)} instance(s) to stop...")
            waiter.wait(InstanceIds=instance_ids)

    def assume_service_role(self, role: str) -> None:
        os.environ.update(assume_role(role).dict())
        os.environ.pop("AWS_PROFILE", None)  # Remove AWS_PROFILE env if it exists

    def handle_error(self, ex: Exception) -> None:
        if isinstance(ex, (ClientError, NoCredentialsError)):
            try:
                handle_boto_error(ex)
            except ClientError as e:
                error_info = e.response.get("Error", {})
                error_code = error_info.get("Code")
                error_message = error_info.get("Message")

                print(f"boto3 error: ({error_code}) {error_message or e}", file=sys.stderr)
                exit(11)

        super().handle_error(ex)

    def update_kubeconfig(self, cluster_name: str, kubeconfig_path: str) -> None:
        shell(
            [
                "aws",
                "eks",
                "--region",
                get_aws_config("region"),
                "update-kubeconfig",
                "--name",
                cluster_name,
                "--kubeconfig",
                kubeconfig_path,
            ],
        )
