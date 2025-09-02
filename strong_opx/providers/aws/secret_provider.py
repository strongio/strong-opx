import logging
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import ClientError
from pydantic.dataclasses import dataclass

from strong_opx.providers.secret_provider import SecretProvider
from strong_opx.template import ObjectTemplate

if TYPE_CHECKING:
    from strong_opx.project import Environment

logger = logging.getLogger(__name__)


@dataclass
class SSMSecretProvider(SecretProvider):
    secret_length: int = 24
    parameter: str = None

    def get_secret(self, environment: "Environment"):
        if self.parameter is None:
            parameter = f"/strong-opx/{environment.project.name}/{environment.name}/vault-secret"
        else:
            parameter = ObjectTemplate(environment.base_context).render(self.parameter)

        ssm = boto3.client("ssm")
        try:
            response = ssm.get_parameter(Name=parameter, WithDecryption=True)
            secret = response["Parameter"]["Value"]
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code != "ParameterNotFound":
                raise e

            logger.info(f"Unable to locate {parameter}. Generating new secret for encryption")
            secret = self.generate_secret()
            ssm.put_parameter(
                Name=parameter,
                Description=f"Strong-OpX Secret for {environment.project.name} ({environment.name})",
                Value=secret,
                Type="SecureString",
                Tags=[
                    {"Key": "Project", "Value": environment.project.name},
                    {"Key": "Environment", "Value": environment.name},
                ],
            )

        return secret


SECRET_PROVIDERS = {
    "aws_ssm": SSMSecretProvider,
}
