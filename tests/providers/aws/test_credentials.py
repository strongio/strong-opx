import datetime
from dataclasses import dataclass
from typing import Optional
from unittest.mock import Mock, call, patch

import pytest

from strong_opx.providers.aws.credentials import AWSCredential, aws_credentials


class GetAWSCredentialSideEffect:
    def __init__(
        self,
        arn: str,
        aws_access_key_id: Optional[str],
        aws_secret_access_key: Optional[str],
        aws_session_token: Optional[str],
        expires: Optional[str],
    ):
        self.arn = arn
        self.values = {
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "aws_session_token": aws_session_token,
            "expires": expires,
        }

    def __call__(self, section, option, fallback):
        if section != self.arn:
            return fallback

        return self.values.get(option) or fallback


class TestGetAWSCredential:
    @dataclass
    class Parameters:
        description: str
        arn: str
        get_config_side_effect: Optional[GetAWSCredentialSideEffect]
        expected_credential: Optional[AWSCredential]

    @dataclass
    class Fixture:
        credential: Optional[AWSCredential]
        expected_credential: Optional[AWSCredential]

    @pytest.fixture(
        ids=lambda x: x.description,
        params=[
            Parameters(
                description="no credentials",
                arn="arn:aws:iam::1234:role/some-role",
                get_config_side_effect=GetAWSCredentialSideEffect(
                    arn="arn:aws:iam::1234:role/some-role",
                    aws_access_key_id=None,
                    aws_secret_access_key=None,
                    aws_session_token=None,
                    expires=None,
                ),
                expected_credential=None,
            ),
            Parameters(
                description="cached credentials",
                arn="arn:aws:iam::1234:role/some-role",
                get_config_side_effect=GetAWSCredentialSideEffect(
                    arn="arn:aws:iam::1234:role/some-role",
                    aws_access_key_id="SOME-KEY",
                    aws_secret_access_key="SOME-SECRET",
                    aws_session_token="SOME-TOKEN",
                    expires=(datetime.datetime.now() + datetime.timedelta(hours=1)).replace(tzinfo=None).isoformat(),
                ),
                expected_credential=AWSCredential(
                    aws_access_key_id="SOME-KEY",
                    aws_secret_access_key="SOME-SECRET",
                    aws_session_token="SOME-TOKEN",
                ),
            ),
            Parameters(
                description="cached credentials but expired",
                arn="arn:aws:iam::1234:role/some-role",
                get_config_side_effect=GetAWSCredentialSideEffect(
                    arn="arn:aws:iam::1234:role/some-role",
                    aws_access_key_id="SOME-KEY",
                    aws_secret_access_key="SOME-SECRET",
                    aws_session_token="SOME-TOKEN",
                    expires=datetime.datetime.now().replace(tzinfo=None).isoformat(),
                ),
                expected_credential=None,
            ),
            Parameters(
                description="cached credentials but for other role",
                arn="arn:aws:iam::1234:role/some-role",
                get_config_side_effect=GetAWSCredentialSideEffect(
                    arn="arn:aws:iam::1234:role/other-role",
                    aws_access_key_id="SOME-KEY",
                    aws_secret_access_key="SOME-SECRET",
                    aws_session_token="SOME-TOKEN",
                    expires=(datetime.datetime.now() + datetime.timedelta(hours=1)).replace(tzinfo=None).isoformat(),
                ),
                expected_credential=None,
            ),
        ],
    )
    @patch.object(aws_credentials, "get", autospec=True)
    def setup(self, get_mock: Mock, request) -> Fixture:
        params: TestGetAWSCredential.Parameters = request.param

        get_mock.side_effect = params.get_config_side_effect
        credential = aws_credentials.get_credential(params.arn)

        return TestGetAWSCredential.Fixture(
            credential=credential,
            expected_credential=params.expected_credential,
        )

    def test_credentials(self, setup: Fixture):
        assert setup.expected_credential == setup.credential


@patch.object(aws_credentials, "remove_section", autospec=True)
@patch.object(aws_credentials, "add_section", autospec=True)
@patch.object(aws_credentials, "set", autospec=True)
@patch.object(aws_credentials, "save", autospec=True)
def test_set_aws_credentials(
    save_mock: Mock,
    set_mock: Mock,
    add_section_mock: Mock,
    remove_section_mock: Mock,
):
    expiry = datetime.datetime.utcnow()
    aws_credentials.set_credential(
        "arn:aws:iam::1234:role/some-role",
        AWSCredential(
            aws_access_key_id="SOME-KEY",
            aws_secret_access_key="SOME-SECRET",
            aws_session_token="SOME-TOKEN",
        ),
        expires=expiry,
    )

    remove_section_mock.assert_called_once_with("arn:aws:iam::1234:role/some-role")
    add_section_mock.assert_called_once_with("arn:aws:iam::1234:role/some-role")
    set_mock.assert_has_calls(
        [
            call("arn:aws:iam::1234:role/some-role", "aws_access_key_id", "SOME-KEY"),
            call("arn:aws:iam::1234:role/some-role", "aws_secret_access_key", "SOME-SECRET"),
            call("arn:aws:iam::1234:role/some-role", "aws_session_token", "SOME-TOKEN"),
            call("arn:aws:iam::1234:role/some-role", "expires", expiry.isoformat()),
        ],
        any_order=True,
    )

    save_mock.assert_called_once()
