import os
from unittest import TestCase, mock

import boto3
from moto import mock_aws

from strong_opx.providers.aws.secret_provider import SSMSecretProvider
from strong_opx.template import ObjectTemplate
from tests.mocks import create_mock_environment, create_mock_project


@mock_aws
@mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-1"})
class SSMSecretProviderTests(TestCase):
    def setUp(self) -> None:
        self.client = boto3.client("ssm", region_name="us-east-1")
        self.project = create_mock_project()
        self.environment = create_mock_environment(project=self.project)

    def test_parameter_name_generated_if_not_specified(self):
        expected_parameter_name = f"/strong-opx/{self.project.name}/{self.environment.name}/vault-secret"

        provider = SSMSecretProvider()
        provider.get_secret(self.environment)

        response = self.client.get_parameter(Name=expected_parameter_name, WithDecryption=True)
        self.assertEqual(response["Parameter"]["Name"], expected_parameter_name)

    @mock.patch.object(ObjectTemplate, "render")
    def test_use_provided_parameter_name(self, mock_render: mock.Mock):
        parameter_name = "some-parameter-name"
        mock_render.return_value = parameter_name

        provider = SSMSecretProvider(parameter=parameter_name)
        provider.get_secret(self.environment)

        response = self.client.get_parameter(Name=parameter_name, WithDecryption=True)
        self.assertEqual(response["Parameter"]["Name"], parameter_name)

        mock_render.assert_called_once_with(parameter_name)

    @mock.patch.object(ObjectTemplate, "render")
    def test_reuse_parameter_value_if_exists(self, mock_render: mock.Mock):
        parameter_name = "some-parameter-name"
        mock_render.return_value = parameter_name

        secret1 = SSMSecretProvider(parameter=parameter_name).get_secret(self.environment)
        secret2 = SSMSecretProvider(parameter=parameter_name).get_secret(self.environment)

        self.assertEqual(secret1, secret2)
