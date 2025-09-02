import os
import sys
from dataclasses import dataclass
from unittest import TestCase, mock
from unittest.mock import patch

import pytest

from strong_opx import __version__
from strong_opx.management import entrypoint
from strong_opx.management.command import BaseCommand
from tests.helper_functions import assert_has_calls_exactly


class EntrypointTests(TestCase):
    @mock.patch.object(sys, "argv", ["strong-opx"])
    def test_no_command_specified(self):
        try:
            entrypoint.main()
        except SystemExit as ex:
            self.assertEqual(ex.code, 2)

    @mock.patch.object(sys, "argv", ["strong-opx", "--project", "some-project", "--env", "some-env", "command"])
    @mock.patch("strong_opx.management.entrypoint._validate_command")
    @mock.patch("strong_opx.management.entrypoint.validate_project_name")
    def test_carry_forward_project_and_env(
        self,
        validate_project_name_mock: mock.Mock,
        validate_command_mock: mock.Mock,
    ):
        mock_command = mock.MagicMock(spec=BaseCommand)

        validate_project_name_mock.side_effect = lambda x: x
        validate_command_mock.return_value.name = "command"
        validate_command_mock.return_value.loader.load_module.return_value.Command = mock_command

        entrypoint.main()

        validate_command_mock.assert_called_once()

        mock_command.assert_called_once()
        mock_command.return_value.run_from_argv.assert_called_once_with(
            ["strong-opx", "command", "--project", "some-project", "--env", "some-env"]
        )

    @mock.patch.object(sys, "argv", ["strong-opx", "--help", "command"])
    @mock.patch("strong_opx.management.entrypoint._validate_command")
    def test_carry_forward_help(self, validate_command_mock: mock.Mock):
        mock_command = mock.MagicMock(spec=BaseCommand)

        validate_command_mock.return_value.name = "command"
        validate_command_mock.return_value.loader.load_module.return_value.Command = mock_command

        entrypoint.main()

        validate_command_mock.assert_called_once()

        mock_command.assert_called_once()
        mock_command.return_value.run_from_argv.assert_called_once_with(["strong-opx", "command", "--help"])

    @mock.patch.object(sys, "argv", ["strong-opx", "--help"])
    @mock.patch("strong_opx.management.entrypoint._validate_command")
    def test_no_carry_forward_help_if_command_is_missing(self, validate_command_mock: mock.Mock):
        mock_command = mock.MagicMock(spec=BaseCommand)

        validate_command_mock.return_value.name = "command"
        validate_command_mock.return_value.loader.load_module.return_value.Command = mock_command

        with self.assertRaises(SystemExit):
            entrypoint.main()

        validate_command_mock.assert_not_called()

    @mock.patch.object(sys, "argv", ["strong-opx", "--version"])
    @mock.patch("strong_opx.management.entrypoint.print")
    def test_print_version(self, print_mock: mock.Mock):
        with self.assertRaises(SystemExit):
            entrypoint.main()

        print_mock.assert_called_once_with(__version__)


class TestCommandNameFromModuleName(TestCase):
    def test_underscore_replacement(self):
        expected = "aws:ec2"
        actual = entrypoint._command_name_from_module_name("aws_ec2")

        self.assertEqual(expected, actual)

    def test_period_splitting(self):
        expected = "baz"
        actual = entrypoint._command_name_from_module_name("foo.bar.baz")

        self.assertEqual(expected, actual)


class TestListCommands:
    @dataclass
    class Fixture:
        actual_return: any
        command_name_from_module_name_mock: mock.Mock
        iter_modules_mock: mock.Mock

    @pytest.fixture
    @patch("strong_opx.management.entrypoint.pkgutil.iter_modules", autospec=True)
    @patch.object(entrypoint, "_command_name_from_module_name", autospec=True)
    def setup(self, command_name_from_module_name_mock: mock.Mock, iter_modules_mock: mock.Mock):
        iter_modules_mock.return_value = [
            ("ignore", "command_1", "ignore"),
            ("ignore", "command_2", "ignore"),
            ("ignore", "command_3", "ignore"),
        ]

        def _add_name_suffix(x):
            return f"{x}_name"

        command_name_from_module_name_mock.side_effect = _add_name_suffix

        actual_return = list(entrypoint._list_commands())

        return self.Fixture(
            actual_return=actual_return,
            command_name_from_module_name_mock=command_name_from_module_name_mock,
            iter_modules_mock=iter_modules_mock,
        )

    def test_should_call_iter_modules_with_commands_path(self, setup: Fixture):
        # I had trouble mocking the import of the 'commands' module. This was the best, valid test I came up with.
        setup.iter_modules_mock.mock_calls[0][0].endswith(os.path.join("strong_opx", "management", "commands"))

    def test_should_get_command_name_for_each_module(self, setup: Fixture):
        assert_has_calls_exactly(
            mock=setup.command_name_from_module_name_mock,
            expected_calls=[mock.call("command_1"), mock.call("command_2"), mock.call("command_3")],
        )

    def test_should_return_expected_commands(self, setup: Fixture):
        expected_return = ["command_1_name", "command_2_name", "command_3_name"]
        assert expected_return == setup.actual_return


class TestListSimilarCommands:
    @pytest.mark.parametrize(
        ids=["one result", "multiple results", "no results"],
        argnames=["user_command", "expected_result"],
        argvalues=[("patato", ["potato"]), ("tamato", ["tomato", "timato"]), ("xxxxxxxxxx", [])],
    )
    @patch.object(entrypoint, "_list_commands", autospec=True)
    def test_one_close_command(self, list_commands_mock: mock.Mock, user_command: str, expected_result: list[str]):
        list_commands_mock.return_value = ["potato", "tomato", "timato"]

        actual_result = entrypoint._list_similar_commands(user_command)

        assert actual_result == expected_result
