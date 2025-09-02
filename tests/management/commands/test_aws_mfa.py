import unittest
from unittest.mock import patch

from botocore.exceptions import ClientError

from strong_opx.exceptions import CommandError
from strong_opx.management.commands.aws_mfa import Command
from strong_opx.providers.aws.credentials import AWSCredential


class TestCommand(unittest.TestCase):
    @patch("strong_opx.management.commands.aws_mfa.AWSCredentialConfig")
    @patch("boto3.Session")
    def test_handle_success(self, mock_boto_session, mock_aws_credential_config):
        mock_sts_client = mock_boto_session.return_value.client.return_value
        mock_sts_client.get_session_token.return_value = {
            "Credentials": {
                "AccessKeyId": "test_access_key",
                "SecretAccessKey": "test_secret_key",
                "SessionToken": "test_session_token",
                "Expiration": "test_expiration",
            }
        }
        mock_aws_credential_config.return_value.has_section.return_value = True
        mock_aws_credential_config.return_value.get.return_value = "test_mfa_device"

        Command().handle(mfa_token="123456", profile="test_profile", duration=3600)

        mock_sts_client.get_session_token.assert_called_once_with(
            DurationSeconds=3600, SerialNumber="test_mfa_device", TokenCode="123456"
        )
        mock_aws_credential_config.return_value.set_credential.assert_called_once_with(
            "test_profile",
            AWSCredential(
                aws_access_key_id="test_access_key",
                aws_secret_access_key="test_secret_key",
                aws_session_token="test_session_token",
            ),
            "test_expiration",
        )

    @patch("strong_opx.management.commands.aws_mfa.AWSCredentialConfig")
    def test_handle_no_mfa_configuration(self, mock_aws_credential_config):
        mock_aws_credential_config.return_value.has_section.return_value = False

        with self.assertRaises(CommandError) as context:
            Command().handle(mfa_token="123456", profile="test_profile", duration=3600)

        self.assertEqual(str(context.exception), "No MFA configuration found for profile test_profile")

    @patch("strong_opx.management.commands.aws_mfa.AWSCredentialConfig")
    @patch("boto3.Session")
    def test_handle_client_error(self, mock_boto_session, mock_aws_credential_config):
        mock_sts_client = mock_boto_session.return_value.client.return_value
        mock_sts_client.get_session_token.side_effect = ClientError(
            {"Error": {"Message": "An error occurred"}}, "GetSessionToken"
        )
        mock_aws_credential_config.return_value.has_section.return_value = True
        mock_aws_credential_config.return_value.get.return_value = "test_mfa_device"

        with self.assertRaises(CommandError) as context:
            Command().handle(mfa_token="123456", profile="test_profile", duration=3600)

        self.assertEqual(str(context.exception), "An error occurred")
