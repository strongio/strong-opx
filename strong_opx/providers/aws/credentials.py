import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from dateutil.parser import parse as parse_dt

from strong_opx.config import CONFIG_DIR, Config

AWS_CREDENTIALS_FILE = os.path.join(os.path.expanduser("~"), ".aws", "credentials")


def mfa_profile_name(profile_name: str) -> str:
    return f"{profile_name}--mfa"


@dataclass
class AWSCredential:
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: str

    def dict(self):
        return {
            "AWS_ACCESS_KEY_ID": self.aws_access_key_id,
            "AWS_SECRET_ACCESS_KEY": self.aws_secret_access_key,
            "AWS_SESSION_TOKEN": self.aws_session_token,
        }


class AWSCredentialConfig(Config):
    def __init__(self, config_path: str = None):
        super().__init__(config_path or AWS_CREDENTIALS_FILE)

    def are_credential_expired(self, profile_name: str) -> bool:
        expiry = self.get(profile_name, "expires", fallback=None)
        if not expiry:
            return True

        expiry_dt = parse_dt(expiry)
        if expiry_dt and datetime.now() < expiry_dt:
            return False

        return True

    def get_credential(self, profile_name: str) -> Optional[AWSCredential]:
        if self.are_credential_expired(profile_name):
            return None

        return AWSCredential(
            aws_access_key_id=self.get(profile_name, "aws_access_key_id", fallback=""),
            aws_secret_access_key=self.get(profile_name, "aws_secret_access_key", fallback=""),
            aws_session_token=self.get(profile_name, "aws_session_token", fallback=""),
        )

    def set_credential(self, profile_name: str, credential: AWSCredential, expires: datetime):
        self.remove_section(profile_name)
        self.add_section(profile_name)
        self.set(profile_name, "aws_access_key_id", credential.aws_access_key_id)
        self.set(profile_name, "aws_secret_access_key", credential.aws_secret_access_key)
        self.set(profile_name, "aws_session_token", credential.aws_session_token)
        self.set(profile_name, "expires", expires.astimezone().replace(tzinfo=None).isoformat())
        self.save()


aws_credentials = AWSCredentialConfig(os.path.join(CONFIG_DIR, "aws-credentials"))
