import argparse
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError
from colorama import Fore as TextColor

from strong_opx.config import system_config
from strong_opx.exceptions import CommandError
from strong_opx.management.command import BaseCommand
from strong_opx.providers.aws import AWSCredentialConfig
from strong_opx.providers.aws.credentials import AWSCredential, mfa_profile_name


def validate_mfa_token(token: str) -> str:
    if len(token) != 6:
        raise argparse.ArgumentTypeError("MFA Token must be 6 digits")

    return token


class Command(BaseCommand):
    help_text = "Refresh AWS Security Token for MFA enabled profiles"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("mfa_token", type=validate_mfa_token, help="OTP from MFA device")
        parser.add_argument("--profile", help="AWS Profile Name", required=True)
        parser.add_argument(
            "--duration",
            type=int,
            default=43200,
            help="The duration, in seconds, that the credentials should remain valid. Default 12 hrs",
        )

    def handle(
        self,
        mfa_token: str,
        profile: Optional[str],
        duration: int,
        **options: Any,
    ) -> None:
        if profile is None:
            profile = system_config.get("aws", "aws_profile", fallback="default")

        aws_config = AWSCredentialConfig()
        section_name = mfa_profile_name(profile)

        if not aws_config.has_section(section_name):
            raise CommandError(f"No MFA configuration found for profile {profile}")

        aws_mfa_device = aws_config.get(section_name, "aws_mfa_device")
        sts = boto3.Session(profile_name=section_name).client("sts")

        try:
            response = sts.get_session_token(
                DurationSeconds=duration,
                SerialNumber=aws_mfa_device,
                TokenCode=mfa_token,
            )["Credentials"]

            credentials = AWSCredential(
                aws_access_key_id=response["AccessKeyId"],
                aws_secret_access_key=response["SecretAccessKey"],
                aws_session_token=response["SessionToken"],
            )
            expiration = response["Expiration"]
        except ClientError as e:
            if e.operation_name == "GetSessionToken":
                raise CommandError(e.response.get("Error", {}).get("Message", "Unknown"))

            raise

        aws_config.set_credential(profile, credentials, expiration)
        print(f"{TextColor.GREEN}AWS Security Token refreshed successfully{TextColor.RESET}")
