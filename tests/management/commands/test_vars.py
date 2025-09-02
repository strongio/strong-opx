import io
from contextlib import redirect_stdout
from dataclasses import dataclass
from unittest import TestCase, mock
from unittest.mock import MagicMock, PropertyMock, create_autospec, patch

import pytest

from strong_opx.exceptions import CommandError
from strong_opx.management.commands.vars import Command
from strong_opx.project import Environment
from strong_opx.template import Context
from tests.mocks import create_mock_environment


def foo():
    return "lazy_foo"


class TestHandleDecrypt:
    @dataclass
    class ATestCase:
        description: str
        context: Context
        expected_lines: list[str]

    test_cases = [
        ATestCase(
            description="Basic context",
            context=Context(hello="world", goodnight="moon"),
            expected_lines=["goodnight: moon", "hello: world"],
        ),
        ATestCase(
            description="Context with a lazy-load value",
            context=Context(hello="world", foo=foo),
            expected_lines=["foo: lazy_foo", "hello: world"],
        ),
    ]

    @pytest.mark.parametrize(
        ids=[test_case.description for test_case in test_cases],
        argnames=["test_case"],
        argvalues=[(test_case,) for test_case in test_cases],
    )
    def test_decrypt_with_basic_context(self, test_case: ATestCase):
        environment = create_autospec(spec=Environment, instance=True)
        type(environment).context = PropertyMock(return_value=test_case.context)

        command = Command()

        with redirect_stdout(io.StringIO()) as stdout_redirect:
            command.handle_decrypt(environment)

        # Get lines written to stdout and sort them alphabetically
        stdout_redirect.seek(0)
        lines = stdout_redirect.readlines()
        lines = list(sorted([line.strip() for line in lines]))

        assert test_case.expected_lines == lines


class CommandTest(TestCase):
    def test_handle_raises_error_when_no_operation_provided(self):
        with self.assertRaises(CommandError):
            Command().handle()

    def test_handle_calls_handle_encrypt_when_operation_is_encrypt(self):
        cmd = Command()
        cmd.handle_encrypt = MagicMock()
        cmd.handle(operation="encrypt")
        cmd.handle_encrypt.assert_called_once()

    def test_handle_calls_handle_decrypt_when_operation_is_decrypt(self):
        cmd = Command()
        cmd.handle_decrypt = MagicMock()
        cmd.handle(operation="decrypt")
        cmd.handle_decrypt.assert_called_once()

    def test_handle_encrypt_raises_error_when_no_value_or_vars_provided(self):
        with self.assertRaises(CommandError):
            Command().handle_encrypt(environment=None, vars=None, value=None)

    @patch("builtins.print")
    @patch("strong_opx.management.commands.vars.VaultCipher")
    def test_handle_encrypt_calls_vault_cipher_encrypt_with_context_var(
        self, vault_cipher_mock: MagicMock, print_mock: MagicMock
    ):
        environment = create_mock_environment()
        environment.context = Context({"VAR1": "secret1", "VAR2": "secret2"})
        environment.vault_secret = "password"

        vault_cipher_mock.encrypt.return_value = "some-encrypted-value-line-1\nsome-encrypted-value-line-2"
        Command().handle_encrypt(environment=environment, vars=["VAR1", "VAR2"])

        vault_cipher_mock.encrypt.assert_has_calls(
            [
                mock.call("secret1", "password"),
                mock.call("secret2", "password"),
            ]
        )

        print_mock.assert_has_calls(
            [
                mock.call("VAR1: !vault |"),
                mock.call(" ", "some-encrypted-value-line-1"),
                mock.call(" ", "some-encrypted-value-line-2"),
                mock.call(),
                mock.call("VAR2: !vault |"),
                mock.call(" ", "some-encrypted-value-line-1"),
                mock.call(" ", "some-encrypted-value-line-2"),
                mock.call(),
            ]
        )

    @patch("builtins.print")
    @patch("strong_opx.management.commands.vars.VaultCipher")
    def test_handle_encrypt_calls_vault_cipher_encrypt_with_value(
        self, vault_cipher_mock: MagicMock, print_mock: MagicMock
    ):
        environment = MagicMock()
        environment.vault_secret = "password"
        vault_cipher_mock.encrypt.return_value = "some-encrypted-value-line-1\nsome-encrypted-value-line-2"

        Command().handle_encrypt(environment=environment, vars=None, value="secret1")

        vault_cipher_mock.encrypt.assert_called_once_with("secret1", "password")
        print_mock.assert_called_once_with("some-encrypted-value-line-1\nsome-encrypted-value-line-2")
