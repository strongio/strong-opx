import argparse
from dataclasses import dataclass
from unittest.mock import Mock, call, create_autospec, patch

import pytest

from strong_opx.management.commands.k8s import Command
from strong_opx.platforms.kubernetes import KubernetesPlatform
from strong_opx.project import Environment, Project


class TestK8sCommandArguments:
    @dataclass
    class Fixture:
        actual: dict
        expected: dict
        mock_super_add_arguments: Mock
        parser: argparse.ArgumentParser
        command: Command

    @dataclass
    class Params:
        input_args: list
        expected_args: dict

    @pytest.fixture(
        ids=["minimum args"],
        params=[
            Params(
                input_args=["dashboard", "up"],
                expected_args={"operation": "up", "plugin": "dashboard", "update_config": False},
            )
        ],
    )
    @patch("strong_opx.management.commands.k8s.ProjectCommand.add_arguments", autospec=True)
    def setup(self, mock_super_add_arguments, request):
        arg_parser = argparse.ArgumentParser()
        command = Command()
        command.add_arguments(parser=arg_parser)

        return TestK8sCommandArguments.Fixture(
            actual=arg_parser.parse_args(args=request.param.input_args).__dict__,
            expected=request.param.expected_args,
            mock_super_add_arguments=mock_super_add_arguments,
            parser=arg_parser,
            command=command,
        )

    def test_args(self, setup: Fixture):
        assert setup.actual == setup.expected

    def test_super_add_arguments_called(self, setup: Fixture):
        setup.mock_super_add_arguments.assert_called_once_with(setup.command, setup.parser)


class TestK8sCommandHandle:
    @dataclass
    class Fixture:
        mock_environment: Mock
        mock_os: Mock
        expected_os_remove_calls: list
        mock_project: Mock
        mock_platform: KubernetesPlatform
        additional_args: tuple[str, ...]

    @dataclass
    class Params:
        update_config: bool
        os_path_exists: bool
        expected_os_remove_calls: list
        additional_args: tuple[str, ...]

    @pytest.fixture(
        ids=["do not update config", "update config that does not exist", "update config", "additional params"],
        params=[
            Params(update_config=False, os_path_exists=False, expected_os_remove_calls=[], additional_args=()),
            Params(update_config=True, os_path_exists=False, expected_os_remove_calls=[], additional_args=()),
            Params(
                update_config=True,
                os_path_exists=True,
                expected_os_remove_calls=[call("some Kube path")],
                additional_args=(),
            ),
            Params(
                update_config=True,
                os_path_exists=True,
                expected_os_remove_calls=[call("some Kube path")],
                additional_args=("var1", "var2"),
            ),
        ],
    )
    @patch("strong_opx.management.commands.k8s.os", autospec=True)
    def setup(
        self,
        mock_os,
        request,
    ):
        mock_os.path.exists.return_value = request.param.os_path_exists

        mock_project = create_autospec(Project)
        mock_environment = create_autospec(Environment)
        mock_platform = create_autospec(KubernetesPlatform)
        mock_platform.kube_config_path = "some Kube path"

        mock_environment.select_platform.return_value = mock_platform

        Command().handle(
            project=mock_project,
            plugin="some-plugin",
            operation="some-operation",
            update_config=request.param.update_config,
            environment=mock_environment,
            additional_args=request.param.additional_args,
        )

        return TestK8sCommandHandle.Fixture(
            mock_environment=mock_environment,
            mock_project=mock_project,
            mock_os=mock_os,
            mock_platform=mock_platform,
            expected_os_remove_calls=request.param.expected_os_remove_calls,
            additional_args=request.param.additional_args,
        )

    def test_os_remove(self, setup: Fixture):
        assert setup.mock_os.remove.mock_calls == setup.expected_os_remove_calls

    def test_plugin(self, setup: Fixture):
        setup.mock_platform.plugin.assert_called_once_with("some-plugin")

    def test_operation(self, setup: Fixture):
        setup.mock_platform.plugin("some-plugin").run.assert_called_once_with("some-operation", *setup.additional_args)
