import unittest
from unittest.mock import MagicMock, patch

import boto3

from strong_opx.exceptions import CommandError
from strong_opx.management.commands.aws_configure import Command, select_mfa_device


class TestSelectMfaDevice(unittest.TestCase):
    mock_boto_client = MagicMock()

    def setUp(self):
        self.mock_boto_client.reset_mock()
        self.mock_sts_client = MagicMock()
        self.mock_iam_client = MagicMock()

        def _mock_boto_client(service_name):
            if service_name == "sts":
                return self.mock_sts_client
            elif service_name == "iam":
                return self.mock_iam_client
            else:
                raise ValueError(f"Unknown service name: {service_name}")

        self.mock_boto_client.side_effect = _mock_boto_client

    @patch("boto3.Session.client", new=mock_boto_client)
    def test_select_mfa_device_single_device(self):
        self.mock_sts_client.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789012:user/test-user"}

        self.mock_iam_client.list_mfa_devices.return_value = {
            "MFADevices": [{"SerialNumber": "arn:aws:iam::123456789012:mfa/test-mfa-device"}]
        }

        session = boto3.Session()
        mfa_device = select_mfa_device(session)
        self.assertEqual(mfa_device, "arn:aws:iam::123456789012:mfa/test-mfa-device")

    @patch("boto3.Session.client", new=mock_boto_client)
    @patch(
        "strong_opx.management.commands.aws_configure.select_prompt",
        return_value="arn:aws:iam::123456789012:mfa/test-mfa-device-1",
    )
    def test_select_mfa_device_multiple_devices(self, mock_boto_client):
        self.mock_sts_client.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789012:user/test-user"}

        self.mock_iam_client.list_mfa_devices.return_value = {
            "MFADevices": [
                {"SerialNumber": "arn:aws:iam::123456789012:mfa/test-mfa-device-1"},
                {"SerialNumber": "arn:aws:iam::123456789012:mfa/test-mfa-device-2"},
            ]
        }

        session = boto3.Session()
        mfa_device = select_mfa_device(session)
        self.assertEqual(mfa_device, "arn:aws:iam::123456789012:mfa/test-mfa-device-1")

    @patch("boto3.Session.client", new=mock_boto_client)
    def test_select_mfa_device_no_devices(self):
        self.mock_sts_client.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789012:user/test-user"}

        self.mock_iam_client.list_mfa_devices.return_value = {"MFADevices": []}

        session = boto3.Session()
        mfa_device = select_mfa_device(session)
        self.assertIsNone(mfa_device)


class TestCommand(unittest.TestCase):
    mock_boto_client = MagicMock()

    @patch("strong_opx.management.commands.aws_configure.AWSCredentialConfig")
    @patch("strong_opx.management.commands.aws_configure.select_mfa_device")
    def test_profile_already_exists(self, mock_select_mfa_device, mock_aws_credential_config):
        mock_aws_config = mock_aws_credential_config.return_value
        mock_aws_config.config_path = "dummy_file_path"
        mock_aws_config.has_section.return_value = True

        with (
            patch("builtins.input", side_effect=["test_profile", "test_access_key", "test_secret_key"]),
            self.assertRaises(CommandError) as cm,
        ):
            Command().handle()

        self.assertEqual(str(cm.exception), 'Profile "test_profile" already exists in dummy_file_path')

    @patch("strong_opx.management.commands.aws_configure.AWSCredentialConfig")
    @patch("strong_opx.management.commands.aws_configure.select_mfa_device")
    def test_no_mfa(self, mock_select_mfa_device, mock_aws_credential_config):
        mock_select_mfa_device.return_value = None
        mock_aws_config = mock_aws_credential_config.return_value
        mock_aws_config.has_section.return_value = False

        with patch("builtins.input", side_effect=["test_profile", "test_access_key", "test_secret_key"]):
            Command().handle()

        mock_aws_config.add_section.assert_called_once_with("test_profile")
        mock_aws_config.set.assert_any_call("test_profile", "aws_access_key_id", "test_access_key")
        mock_aws_config.set.assert_any_call("test_profile", "aws_secret_access_key", "test_secret_key")
        mock_aws_config.save.assert_called_once()

    @patch("strong_opx.management.commands.aws_configure.AWSCredentialConfig")
    @patch("strong_opx.management.commands.aws_configure.select_mfa_device")
    def test_with_mfa(self, mock_select_mfa_device, mock_aws_credential_config):
        mock_aws_config = mock_aws_credential_config.return_value
        mock_aws_config.has_section.return_value = False

        mock_select_mfa_device.return_value = "arn:aws:iam::123456789012:mfa/test_user"

        with patch("builtins.input", side_effect=["test_profile", "test_access_key", "test_secret_key"]):
            Command().handle()

        mock_aws_config.add_section.assert_called_once_with("test_profile--mfa")
        mock_aws_config.set.assert_any_call("test_profile--mfa", "aws_access_key_id", "test_access_key")
        mock_aws_config.set.assert_any_call("test_profile--mfa", "aws_secret_access_key", "test_secret_key")
        mock_aws_config.set.assert_any_call(
            "test_profile--mfa", "aws_mfa_device", "arn:aws:iam::123456789012:mfa/test_user"
        )
        mock_aws_config.save.assert_called_once()
