import argparse
import os.path
from dataclasses import dataclass
from unittest import TestCase
from unittest.mock import MagicMock, Mock, call, create_autospec, patch

import pytest

from strong_opx.config.hierarchical import HierarchicalConfig
from strong_opx.management.commands.docker_build import Command, get_ecr_tags_to_apply
from strong_opx.providers.container_registry import AbstractContainerRegistry
from tests.mocks import create_mock_environment, create_mock_project


class TestDockerCommandArguments:
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
        ids=[
            "minimum args",
            "change name",
            "with push",
            "with ssh",
            "with ssh & key",
            "change tag",
            "invalid tag None",
            "invalid tag white space",
            "valid build-args",
        ],
        params=[
            Params(
                input_args=["foo"],
                expected_args={
                    "path": "foo",
                    "name": None,
                    "docker_push": False,
                    "mount_ssh": False,
                    "ssh_key": None,
                    "docker_tags": [],
                    "build_args": None,
                },
            ),
            Params(
                input_args=["--name", "newName", "foo"],
                expected_args={
                    "path": "foo",
                    "name": "newName",
                    "docker_push": False,
                    "mount_ssh": False,
                    "ssh_key": None,
                    "docker_tags": [],
                    "build_args": None,
                },
            ),
            Params(
                input_args=["--push", "foo"],
                expected_args={
                    "path": "foo",
                    "name": None,
                    "docker_push": True,
                    "mount_ssh": False,
                    "ssh_key": None,
                    "docker_tags": [],
                    "build_args": None,
                },
            ),
            Params(
                input_args=["--ssh", "foo"],
                expected_args={
                    "path": "foo",
                    "name": None,
                    "docker_push": False,
                    "mount_ssh": True,
                    "ssh_key": None,
                    "docker_tags": [],
                    "build_args": None,
                },
            ),
            Params(
                input_args=["--ssh", "--ssh-key", "some-key", "foo"],
                expected_args={
                    "path": "foo",
                    "name": None,
                    "docker_push": False,
                    "mount_ssh": True,
                    "ssh_key": "some-key",
                    "docker_tags": [],
                    "build_args": None,
                },
            ),
            Params(
                input_args=["foo", "--tag", "coolTag"],
                expected_args={
                    "path": "foo",
                    "name": None,
                    "docker_push": False,
                    "mount_ssh": False,
                    "ssh_key": None,
                    "docker_tags": ["coolTag"],
                    "build_args": None,
                },
            ),
            Params(
                input_args=["foo", "--tag", None],
                expected_args={
                    "path": "foo",
                    "name": None,
                    "docker_push": False,
                    "mount_ssh": False,
                    "ssh_key": None,
                    "docker_tags": ["latest"],
                    "build_args": None,
                },
            ),
            Params(
                input_args=["foo", "--tag", "     "],
                expected_args={
                    "path": "foo",
                    "name": None,
                    "docker_push": False,
                    "mount_ssh": False,
                    "ssh_key": None,
                    "docker_tags": ["latest"],
                    "build_args": None,
                },
            ),
            Params(
                input_args=["foo", "--build-arg", "arg1", "arg2"],
                expected_args={
                    "path": "foo",
                    "name": None,
                    "docker_push": False,
                    "mount_ssh": False,
                    "ssh_key": None,
                    "docker_tags": [],
                    "build_args": ["arg1", "arg2"],
                },
            ),
        ],
    )
    @patch("strong_opx.management.commands.docker_build.ProjectCommand.add_arguments", autospec=True)
    def setup(self, mock_super_add_arguments, request):
        arg_parser = argparse.ArgumentParser()
        command = Command()
        command.add_arguments(parser=arg_parser)

        return TestDockerCommandArguments.Fixture(
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


class CommandTests(TestCase):
    def setUp(self) -> None:
        self.mock_config = create_autospec(HierarchicalConfig)
        self.mock_config.docker_executable = "aDocker"
        self.mock_config.git_ssh_key = "aSshKey"

        self.mock_project = create_mock_project(config=self.mock_config, provider="aws")
        self.mock_environment = create_mock_environment(project=self.mock_project)

    def invoke_handle(self, **kwargs):
        path = os.path.join(self.mock_project.path, "bar")
        os.makedirs(path, exist_ok=True)

        kwargs.setdefault("docker_tags", [])
        Command().handle(
            path=path, project=self.mock_project, environment=self.mock_environment, additional_args=(), **kwargs
        )

    @patch("strong_opx.management.commands.docker_build.shell", autospec=True)
    def test_handle_with_custom_name(self, shell_mock: Mock):
        self.invoke_handle(name="foo")
        shell_mock.assert_called_once_with(["aDocker", "buildx", "build", "-t", "foo:latest", "/tmp/unittest/bar"])

    @patch("strong_opx.management.commands.docker_build.shell", autospec=True)
    def test_handle_with_default_name(self, shell_mock: Mock):
        self.invoke_handle()
        shell_mock.assert_called_once_with(["aDocker", "buildx", "build", "-t", "bar:latest", "/tmp/unittest/bar"])

    @patch("strong_opx.management.commands.docker_build.shell", autospec=True)
    def test_handle_with_custom_tags(self, shell_mock: Mock):
        self.invoke_handle(docker_tags=["tag1", "tag2"])
        shell_mock.assert_called_once_with(
            ["aDocker", "buildx", "build", "-t", "bar:latest", "-t", "bar:tag1", "-t", "bar:tag2", "/tmp/unittest/bar"]
        )

    @patch.dict(os.environ, clear=True)
    @patch("strong_opx.management.commands.docker_build.shell", autospec=True)
    @patch("strong_opx.management.commands.docker_build.ssh_agent", autospec=True)
    def test_handle_with_mount_ssh(self, mock_ssh_agent: Mock, shell_mock: Mock):
        self.invoke_handle(mount_ssh=True)
        shell_mock.assert_called_once_with(
            ["aDocker", "buildx", "build", "-t", "bar:latest", "--ssh", "default", "/tmp/unittest/bar"]
        )

        with self.subTest("ssh_agent is engaged"):
            mock_ssh_agent.assert_called_once_with("aSshKey")
            mock_ssh_agent.return_value.__enter__.assert_called_once_with()

    @patch.dict(os.environ, clear=True)
    @patch("strong_opx.management.commands.docker_build.shell", new=Mock())
    @patch("strong_opx.management.commands.docker_build.ssh_agent", autospec=True)
    def test_handle_with_mount_ssh_and_custom_ssh_key(self, mock_ssh_agent: Mock):
        self.invoke_handle(mount_ssh=True, ssh_key="some-user-specified-key")
        with self.subTest("ssh_agent is engaged"):
            mock_ssh_agent.assert_called_once_with("some-user-specified-key")
            mock_ssh_agent.return_value.__enter__.assert_called_once_with()

    @patch.dict(os.environ, clear=True)
    @patch("strong_opx.management.commands.docker_build.shell", autospec=True)
    @patch("strong_opx.providers.aws.container_registry.ContainerRegistry.login", autospec=True)
    @patch("strong_opx.management.commands.docker_build.get_ecr_tags_to_apply", autospec=True)
    def test_handle_with_docker_push(self, get_ecr_tags_to_apply_mock: Mock, login_mock: Mock, shell_mock: Mock):
        get_ecr_tags_to_apply_mock.return_value = ("some-repo-url", {"some-repo-url:latest", "some-repo-url:some-tag"})

        self.invoke_handle(docker_push=True)
        shell_mock.assert_called_once_with(
            [
                "aDocker",
                "buildx",
                "build",
                "-t",
                "some-repo-url:latest",
                "-t",
                "some-repo-url:some-tag",
                "--push",
                "--cache-to",
                "type=inline",
                "--cache-from",
                "some-repo-url:latest",
                "/tmp/unittest/bar",
            ]
        )

        login_mock.assert_called_once()

    @patch("strong_opx.management.commands.docker_build.shell", autospec=True)
    def test_handle_with_custom_build_args(self, shell_mock: Mock):
        require_mock = self.mock_environment.context.require
        require_mock.return_value = {"VAR1": "1", "VAR2": "2"}

        self.invoke_handle(build_args=["VAR1", "VAR2"])
        shell_mock.assert_called_once_with(
            [
                "aDocker",
                "buildx",
                "build",
                "-t",
                "bar:latest",
                "--build-arg",
                "VAR1=1",
                "--build-arg",
                "VAR2=2",
                "/tmp/unittest/bar",
            ]
        )

        with self.subTest("context.require is called"):
            require_mock.assert_called_once_with("VAR1", "VAR2")

    def test_get_ecr_tags_to_apply(self):
        mock_registry = MagicMock(spec=AbstractContainerRegistry)
        mock_registry.get_or_create_repository_uri.return_value = "some-repo-url"
        mock_registry.get_latest_revision.return_value = 1
        mock_registry.get_repository_uri.return_value = "some-repo-url"
        mock_registry.tag_from_revision.return_value = "unittest-2.some-hash"

        repo_uri, tags = get_ecr_tags_to_apply(
            registry=mock_registry,
            environment=self.mock_environment,
            repository_name="someRepo",
            docker_tag=["TAG1", "TAG2"],
        )

        self.assertEqual(repo_uri, "some-repo-url")
        self.assertSetEqual(
            {
                "some-repo-url:TAG1",
                "some-repo-url:TAG2",
                "some-repo-url:latest",
                "some-repo-url:unittest-latest",
                "some-repo-url:unittest-2.some-hash",
            },
            tags,
        )

        mock_registry.get_or_create_repository_uri.assert_called_once_with("someRepo")
        mock_registry.tag_from_revision.assert_called_once_with(2)
