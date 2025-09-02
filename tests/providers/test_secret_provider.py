import unittest

from strong_opx.providers.secret_provider import SecretProvider


class SecretProviderTests(unittest.TestCase):
    def test_generate_secret(self):
        provider = SecretProvider()
        provider.secret_length = 24
        secret = provider.generate_secret()

        # Check that the secret has the expected length
        self.assertEqual(len(secret), provider.secret_length)

        # Check that the secret only contains alphanumeric characters
        self.assertTrue(secret.isalnum())
