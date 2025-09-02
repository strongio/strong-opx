import os
import re
from datetime import datetime
from functools import lru_cache
from typing import Any

import boto3

from strong_opx.config import system_config
from strong_opx.providers.aws.credentials import AWSCredential, aws_credentials

SERVICE_ROLE_ARN_RE = re.compile(r"^arn:aws:iam::[0-9]+:role/.+$")

DUPLICATE_HYPHENS_RE = re.compile(r"-{2,}")
ROLE_SESSION_NAME_INVALID_CHARS_RE = re.compile(r"[^\w+=,.@-]")


@lru_cache(maxsize=1)
def get_caller_identity() -> dict[str, Any]:
    return boto3.client("sts").get_caller_identity()


def get_current_account_id() -> str:
    profile = os.getenv("AWS_PROFILE", "default")
    account_id = system_config.get(f"aws:{profile}", "account_id", fallback=None)
    if account_id is None:
        account_id = get_caller_identity()["Account"]
        system_config.set(f"aws:{profile}", "account_id", account_id)

    return account_id


def get_current_user_id() -> str:
    return get_caller_identity()["UserId"]


def _assume_role(arn: str) -> tuple[AWSCredential, datetime]:
    client = boto3.client("sts")

    role_session_name = DUPLICATE_HYPHENS_RE.sub(
        "-", ROLE_SESSION_NAME_INVALID_CHARS_RE.sub("-", f"StrongOpX-{get_current_user_id()}")
    )

    response = client.assume_role(
        RoleArn=arn,
        RoleSessionName=role_session_name,
    )

    credentials_dict = response["Credentials"]
    credential = AWSCredential(
        aws_access_key_id=credentials_dict["AccessKeyId"],
        aws_secret_access_key=credentials_dict["SecretAccessKey"],
        aws_session_token=credentials_dict["SessionToken"],
    )
    return credential, credentials_dict["Expiration"]


def assume_role(arn: str) -> AWSCredential:
    if not SERVICE_ROLE_ARN_RE.match(arn):
        raise ValueError(f"Invalid service role ARN: {arn}")

    credential = aws_credentials.get_credential(arn)
    if credential is None:
        print(f"Assuming role: {arn}")
        credential, expires = _assume_role(arn)
        aws_credentials.set_credential(arn, credential, expires)
    else:
        print(f"Using cached credentials for: {arn}")

    return credential
