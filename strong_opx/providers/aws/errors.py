import os
from typing import Union

from botocore.exceptions import ClientError, NoCredentialsError
from colorama import Style

from strong_opx.exceptions import CommandError, RepositoryNotFoundException
from strong_opx.project import Project
from strong_opx.providers.aws.credentials import AWSCredentialConfig


class CredentialError(CommandError):
    def __str__(self):
        project = Project.current()
        profile_name = project.config.get("aws", "aws_profile", fallback=None)

        if profile_name is None:
            message = (
                f"No AWS profile is not configured for current project ({project.name})."
                "\n\n"
                "Configure it using the following command:"
                "\n\n"
                f"{Style.BRIGHT}    strong-opx config aws.aws_profile <aws-profile-name-here> --project "
                f"{project.name}{Style.RESET_ALL}\n"
            )
        else:
            message = (
                f'No credentials found for profile "{profile_name}"'
                "\n\n"
                f"To configured AWS credentials for profile {profile_name}, run the following command:"
                "\n\n"
                f"{Style.BRIGHT}    strong-opx aws:configure --profile {profile_name}{Style.RESET_ALL}\n"
            )

        return message


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


def handle_boto_error(ex: Union[ClientError, NoCredentialsError], ignore: tuple[str, ...] = ()) -> None:
    if isinstance(ex, NoCredentialsError):
        raise CredentialError()

    error = (ex.response or {}).get("Error", {})
    code = error.get("Code")
    if code in ignore:
        return  # Ignore this exception

    constructor = AWS_ERROR_CODE_TO_EXCEPTION.get(code)
    if not constructor:
        raise

    message = error.get("Message", str(ex))
    raise constructor(message)
