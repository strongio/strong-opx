from ansible.parsing.vault import CIPHER_MAPPING, AnsibleVaultError, VaultSecret

from strong_opx.exceptions import VaultError

DEFAULT_CIPHER_NAME = "AES256"


class VaultCipher:
    def __init__(self, ciphertext: str, cipher_name: str = DEFAULT_CIPHER_NAME, version: str = "1.0"):
        self.version = version
        self.ciphertext = ciphertext
        self.cipher_name = cipher_name

    def __str__(self):
        header_parts = ["$STRONG_OPX_VAULT", self.version, self.cipher_name]
        header = ";".join(header_parts)

        vault_text = [header]
        vault_text += [self.ciphertext[i : i + 80] for i in range(0, len(self.ciphertext), 80)]

        return "\n".join(vault_text)

    def __call__(self) -> str:
        from strong_opx.project import Project

        return self.decrypt(Project.current().selected_environment.vault_secret)

    def decrypt(self, secret: str) -> str:
        cipher_cls = CIPHER_MAPPING[self.cipher_name]
        ciphertext = self.ciphertext.encode("utf8", errors="surrogate_or_strict")

        vault_secret = VaultSecret(secret.encode("utf8", errors="surrogate_or_strict"))

        try:
            return cipher_cls().decrypt(ciphertext, vault_secret).decode("utf8")
        except AnsibleVaultError:
            raise VaultError("Decryption failed. Did you copied from other environment?")

    @classmethod
    def encrypt(cls, value: str, secret: str, cipher_name: str = DEFAULT_CIPHER_NAME) -> "VaultCipher":
        cipher_cls = CIPHER_MAPPING[cipher_name]
        cipher_text = (
            cipher_cls()
            .encrypt(
                value.encode("utf8", errors="surrogate_or_strict"),
                VaultSecret(secret.encode("utf8", errors="surrogate_or_strict")),
            )
            .decode("utf8")
        )

        return VaultCipher(ciphertext=cipher_text, cipher_name=cipher_name)

    @classmethod
    def parse(cls, envelope: str) -> "VaultCipher":
        lines = envelope.splitlines()
        header = lines[0].strip().split(";")

        version = header[1].strip()
        cipher_name = header[2].strip()

        ciphertext = "".join(lines[1:])
        return cls(ciphertext=ciphertext, cipher_name=cipher_name, version=version)
