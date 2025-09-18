from unittest import TestCase, mock

from azure.core.exceptions import ResourceNotFoundError

from strong_opx.providers import SecretProvider
from strong_opx.providers.azure.secret_provider import AzureKeyVaultSecretProvider
from strong_opx.template import ObjectTemplate
from tests.mocks import create_mock_environment, create_mock_project


class AzureKeyVaultSecretProviderTests(TestCase):
    def setUp(self) -> None:
        self.project = create_mock_project()
        self.environment = create_mock_environment(project=self.project)

    @mock.patch.object(SecretProvider, "generate_secret")
    @mock.patch("strong_opx.providers.azure.secret_provider.DefaultAzureCredential")
    @mock.patch("strong_opx.providers.azure.secret_provider.SecretClient")
    @mock.patch.object(ObjectTemplate, "render")
    def test_get_secret(self, mock_render, mock_secret_client, mock_credential, mock_generate_secret):
        keyvault_url = "https://some-keyvault-url.vault.azure.net"
        parameter_name = "some-parameter-name"

        mock_render.side_effect = [parameter_name, keyvault_url]

        mock_secret_client.return_value.get_secret.side_effect = ResourceNotFoundError("Not found")

        provider = AzureKeyVaultSecretProvider(keyvault_url=keyvault_url, parameter=parameter_name)

        secret = provider.get_secret(self.environment)

        mock_credential.assert_called_once()
        mock_secret_client.return_value.get_secret.assert_called_once_with(parameter_name)
        mock_secret_client.return_value.set_secret.assert_called_once_with(
            name=parameter_name,
            value=mock_generate_secret.return_value,
            tags={"Project": self.project.name, "Environment": self.environment.name},
        )
        mock_generate_secret.assert_called_once()
        self.assertEqual(secret, mock_generate_secret.return_value)
