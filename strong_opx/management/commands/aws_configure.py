import re
from typing import Any, Optional

import boto3
from colorama import Fore as TextColor

from strong_opx.exceptions import CommandError
from strong_opx.management.command import BaseCommand
from strong_opx.providers.aws import AWSCredentialConfig
from strong_opx.providers.aws.credentials import mfa_profile_name
from strong_opx.utils.prompt import select_prompt

MFA_ARN_RE = re.compile(r"arn:aws:iam::(?P<account_id>\d+):mfa/(?P<username>.+)")
USER_ARN_RE = re.compile(r"arn:aws:iam::(?P<account_id>\d+):user/(?P<username>.+)")


def prompt_until_valid(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value


def select_mfa_device(session) -> Optional[str]:
    caller_arn = session.client("sts").get_caller_identity()["Arn"]
    match = USER_ARN_RE.match(caller_arn)
    if not match:
        return None  # Not an IAM user; assume no MFA

    username = match.group("username")
    all_2fa_devices = session.client("iam").list_mfa_devices(UserName=username)["MFADevices"]

    mfa_devices = [device for device in all_2fa_devices if MFA_ARN_RE.match(device["SerialNumber"])]

    if not mfa_devices:
        return None  # No MFA device

    if len(mfa_devices) > 1:
        mfa_serial_number = select_prompt(
            "Select MFA Device",
            [device["SerialNumber"] for device in mfa_devices],
        )
    else:
        mfa_serial_number = mfa_devices[0]["SerialNumber"]

    return mfa_serial_number


class Command(BaseCommand):
    help_text = "Configure AWS credentials"

    def handle(self, **options: Any) -> None:
        profile_name = prompt_until_valid("Profile name: ")

        aws_config = AWSCredentialConfig()
        aws_access_key_id = prompt_until_valid("AWS Access Key ID: ")
        aws_secret_access_key = prompt_until_valid("AWS Secret Access Key: ")

        boto3_session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        section_name = profile_name
        mfa_device = select_mfa_device(boto3_session)
        if mfa_device:
            section_name = mfa_profile_name(profile_name)

        if aws_config.has_section(section_name):
            raise CommandError(f'Profile "{profile_name}" already exists in {aws_config.config_path}')

        aws_config.add_section(section_name)
        aws_config.set(section_name, "aws_access_key_id", aws_access_key_id)
        aws_config.set(section_name, "aws_secret_access_key", aws_secret_access_key)

        if mfa_device:
            aws_config.set(section_name, "aws_mfa_device", mfa_device)

        aws_config.save()
        print(f'{TextColor.GREEN}Profile "{profile_name}" configured successfully{TextColor.RESET}')

        if mfa_device:
            print(
                "\n"
                "MFA is enabled for this profile. Run following command to get temporary credentials:\n\n"
                f"    strong-opx aws:mfa --profile {profile_name} <mfa-token-code>\n"
            )
