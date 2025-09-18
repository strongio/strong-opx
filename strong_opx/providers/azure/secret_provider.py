from typing import TYPE_CHECKING

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from pydantic.dataclasses import dataclass

from strong_opx.providers.secret_provider import SecretProvider
from strong_opx.template import ObjectTemplate

if TYPE_CHECKING:
    from strong_opx.project import Environment


@dataclass
class AzureKeyVaultSecretProvider(SecretProvider):
    keyvault_url: str
    parameter: str = None
    secret_length: int = 24

    def get_secret(self, environment: "Environment"):
        if self.parameter is None:
            parameter = f"/strong-opx/{environment.project.name}/{environment.name}/vault-secret"
        else:
            parameter = ObjectTemplate(environment.base_context).render(self.parameter)

        keyvault_url = ObjectTemplate(environment.base_context).render(self.keyvault_url)

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=keyvault_url, credential=credential)

        try:
            secret = client.get_secret(parameter).value
        except ResourceNotFoundError:
            secret = self.generate_secret()
            client.set_secret(
                name=parameter,
                value=secret,
                tags={"Project": environment.project.name, "Environment": environment.name},
            )

        return secret


SECRET_PROVIDERS = {
    "keyvault": AzureKeyVaultSecretProvider,
}
