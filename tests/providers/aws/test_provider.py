import os
from unittest import TestCase
from unittest.mock import patch

import boto3
from moto import mock_aws
from parameterized import parameterized

from tests.mocks import create_mock_environment, create_mock_project


class AWSProviderTests(TestCase):
    def setUp(self):
        self.project = create_mock_project(provider="aws")
        self.provider = self.project.provider

        self.provider.__dict__["default_aws_profile"] = None

    @patch("strong_opx.providers.aws.provider.boto3")
    def test_init_project__aws_profile_is_configured(self, boto3_mock):
        self.provider.__dict__["default_aws_profile"] = "some-profile"
        self.provider.init_project(self.project)

        boto3_mock.Session.assert_called_once_with(profile_name="some-profile")

    @parameterized.expand(
        [
            (None, "us-east-1"),
            ("us-west-1", "us-west-1"),
        ]
    )
    @patch("strong_opx.providers.aws.provider.boto3")
    def test_init_project__aws_region(self, region, expected_region, boto3_mock):
        self.provider.config.region = region
        self.provider.init_project(self.project)

        boto3_mock.Session.return_value.client.assert_called_once_with("s3", region_name=expected_region)

    @mock_aws
    def test_init_project_create_bucket(self):
        self.provider.init_project(self.project)

        # Check an-ops-bucket is created
        boto3.client("s3").head_bucket(Bucket="unittest-ops")

    @mock_aws
    @patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-1"})
    def test_init_environment(self):
        environment = create_mock_environment(project=self.project, name="someEnv")
        self.provider.init_environment(environment)

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table("unittest-someEnv-terraform-state")
        self.assertEqual(table.table_status, "ACTIVE")
