import os

from botocore.exceptions import ClientError
from colorama import Style

from strong_opx.exceptions import CommandError, RepositoryNotFoundException
from strong_opx.providers.aws.credentials import AWSCredentialConfig


class CredentialExpiredError(CommandError):
    def __str__(self):
        profile_name = os.getenv("AWS_PROFILE", "default")

        aws_config = AWSCredentialConfig()
        if not aws_config.are_credential_expired(profile_name):
            return super().__str__()

        return (
            f'Credentials for profile "{profile_name}" have expired'
            f"\n\n"
            "MFA is enabled for this profile. Run following command to get temporary credentials:"
            "\n\n"
            f"{Style.BRIGHT}    strong-opx aws:mfa --profile {profile_name} <mfa-token-code>{Style.RESET_ALL}\n"
        )


AWS_ERROR_CODE_TO_EXCEPTION = {
    "ExpiredToken": CredentialExpiredError,
    "RequestExpired": CredentialExpiredError,
    "ExpiredTokenException": CredentialExpiredError,
    "RepositoryNotFoundException": RepositoryNotFoundException,
}


def handle_boto_error(ex: ClientError, ignore: tuple[str, ...] = ()) -> None:
    error = (ex.response or {}).get("Error", {})
    code = error.get("Code")
    if code in ignore:
        return  # Ignore this exception

    constructor = AWS_ERROR_CODE_TO_EXCEPTION.get(code)
    if not constructor:
        raise

    message = error.get("Message", str(ex))
    raise constructor(message)
