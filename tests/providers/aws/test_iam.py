from dataclasses import dataclass
from datetime import datetime
from typing import Union
from unittest.mock import Mock, call, patch

import pytest

from strong_opx.providers.aws.credentials import AWSCredential, AWSCredentialConfig
from strong_opx.providers.aws.iam import _assume_role, assume_role


class TestAssumeRole:
    @dataclass
    class Parameters:
        description: str
        get_credentials_return_value: Union[None, Mock]
        expected_set_aws_credential_call: list

    @dataclass
    class Fixture:
        output: AWSCredential
        mock_system_config_credentials: Mock
        expected_set_aws_credential_call: list

    mock_credentials = Mock(spec=AWSCredential)
    mock_credentials.aws_access_key_id = "original access Key ID"
    mock_credentials.aws_secret_access_key = "original secret Key"
    mock_credentials.aws_session_token = "original session Token"

    mock_assume_role_credentials = Mock(spec=AWSCredential)
    mock_assume_role_credentials.aws_access_key_id = "assumed access Key ID"
    mock_assume_role_credentials.aws_secret_access_key = "assumed secret Key"
    mock_assume_role_credentials.aws_session_token = "assumed session Token"

    @pytest.fixture(
        ids=lambda x: x.description,
        params=[
            Parameters(
                description="assume role",
                get_credentials_return_value=None,
                expected_set_aws_credential_call=[
                    call(
                        "arn:aws:iam::12345678:role/some-role", mock_assume_role_credentials, "fake-assumed-credentials"
                    )
                ],
            ),
            Parameters(
                description="do not assume role",
                get_credentials_return_value=mock_credentials,
                expected_set_aws_credential_call=[],
            ),
        ],
    )
    @patch("strong_opx.providers.aws.iam._assume_role", autospec=True)
    def setup(self, mock_assume_role, request) -> Fixture:
        mock_system_config_credentials = Mock(spec=AWSCredentialConfig)
        mock_system_config_credentials.get_credential.return_value = request.param.get_credentials_return_value

        mock_assume_role.return_value = TestAssumeRole.mock_assume_role_credentials, "fake-assumed-credentials"

        with patch("strong_opx.providers.aws.iam.aws_credentials", new=mock_system_config_credentials):
            output = assume_role(arn="arn:aws:iam::12345678:role/some-role")

        return TestAssumeRole.Fixture(
            output=output,
            mock_system_config_credentials=mock_system_config_credentials,
            expected_set_aws_credential_call=request.param.expected_set_aws_credential_call,
        )

    def test_get_credential_called(self, setup: Fixture):
        setup.mock_system_config_credentials.get_credential.assert_called_once_with(
            "arn:aws:iam::12345678:role/some-role"
        )

    def test__assume_role_called(self, setup: Fixture):
        assert setup.mock_system_config_credentials.set_credential.mock_calls == setup.expected_set_aws_credential_call

    def test_output(self, setup: Fixture):
        credential_source = "assumed" if len(setup.expected_set_aws_credential_call) > 0 else "original"
        assert setup.output.aws_access_key_id == f"{credential_source} access Key ID"
        assert setup.output.aws_secret_access_key == f"{credential_source} secret Key"
        assert setup.output.aws_session_token == f"{credential_source} session Token"


class TestAssumeRolePrivate:
    @dataclass
    class Fixture:
        actual: tuple[AWSCredential, datetime]
        mock_boto3: Mock
        mock_get_current_user_id: Mock
        mock_base_client: Mock

    mock_credentials = Mock(spec=AWSCredential)
    mock_credentials.aws_access_key_id = "original access Key ID"
    mock_credentials.aws_secret_access_key = "original secret Key"
    mock_credentials.aws_session_token = "original session Token"

    @pytest.fixture
    @patch("strong_opx.providers.aws.iam.get_current_user_id", autospec=True)
    @patch("strong_opx.providers.aws.iam.boto3", autospec=True)
    def setup(self, mock_boto3, mock_get_current_user_id) -> Fixture:
        mock_get_current_user_id.return_value = "someUser"
        mock_base_client = Mock()
        mock_base_client.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "key",
                "SecretAccessKey": "secret",
                "SessionToken": "session",
                "Expiration": 1111,
            }
        }
        mock_boto3.client.return_value = mock_base_client
        actual = _assume_role(arn="1234")

        return TestAssumeRolePrivate.Fixture(
            actual=actual,
            mock_boto3=mock_boto3,
            mock_get_current_user_id=mock_get_current_user_id,
            mock_base_client=mock_base_client,
        )

    def test_boto_client(self, setup: Fixture):
        setup.mock_boto3.client.assert_called_once_with("sts")

    def test_get_current_user_id(self, setup: Fixture):
        setup.mock_get_current_user_id.assert_called_once()

    def test_assume_role_called(self, setup: Fixture):
        setup.mock_base_client.assume_role.assert_called_once_with(RoleArn="1234", RoleSessionName="StrongOpX-someUser")

    def test_result(self, setup: Fixture):
        credential, time_expiry = setup.actual
        assert credential == AWSCredential(
            aws_access_key_id="key", aws_secret_access_key="secret", aws_session_token="session"
        )

        assert time_expiry == 1111
