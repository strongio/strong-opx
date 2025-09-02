import unittest
from unittest import mock

from strong_opx.exceptions import VaultError
from strong_opx.vault import VaultCipher


class VaultCipherTests(unittest.TestCase):
    secret = "some-secret"
    plain_text = "some-value"

    def test_encrypt_decrypt(self):
        cipher = VaultCipher.encrypt(self.plain_text, self.secret)
        decrypted_valued = cipher.decrypt(self.secret)
        self.assertEqual(self.plain_text, decrypted_valued)

    def test_parse(self):
        cipher_envelope = str(VaultCipher.encrypt(self.plain_text, self.secret))
        parsed_cipher = VaultCipher.parse(cipher_envelope)

        self.assertEqual(str(parsed_cipher), cipher_envelope)

    def test_decrypt_wrong_secret(self):
        cipher = VaultCipher.encrypt(self.plain_text, self.secret)
        with self.assertRaises(VaultError) as cm:
            cipher.decrypt("wrong-secret")

        self.assertEqual(str(cm.exception), "Decryption failed. Did you copied from other environment?")

    def test_str(self):
        cipher = VaultCipher.encrypt(self.plain_text, self.secret)

        cipher_envelope = str(cipher)
        self.assertTrue(cipher_envelope.startswith("$STRONG_OPX_VAULT;1.0;AES256\n"))

    def test_str__lines_should_be_less_than_80_chars(self):
        cipher = VaultCipher.encrypt(self.plain_text, self.secret)

        cipher_envelope = str(cipher)
        for line in cipher_envelope.splitlines():
            self.assertLessEqual(len(line), 80)

    @mock.patch("strong_opx.project.Project")
    def test_call_should_resolve_secret_from_project(self, project_mock: mock.Mock):
        project_mock.current.return_value.selected_environment.vault_secret = self.secret

        cipher = VaultCipher.encrypt(self.plain_text, self.secret)
        self.assertEqual(cipher(), self.plain_text)
