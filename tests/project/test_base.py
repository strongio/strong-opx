from dataclasses import dataclass
from typing import Union
from unittest import TestCase, mock
from unittest.mock import Mock, patch

import pytest
from resolvelib.providers import AbstractProvider

from strong_opx.exceptions import ProcessError
from strong_opx.helm import HelmConfig
from strong_opx.project import Environment
from strong_opx.project.base import Project
from strong_opx.project.vars import VariableConfig
from strong_opx.providers.secret_provider import SecretProvider
from tests.mocks import create_mock_project


@dataclass
class Fixture:
    project: any
    actual_result: Union[Mock, Environment]
    mock_load_environment: Mock


@pytest.fixture()
@patch("strong_opx.project.base.load_environment", autospec=True)
def setup(mock_load_environment: Mock, monkeypatch) -> Fixture:
    project: Project = Project(
        name="project_name",
        path="the_path",
        provider=Mock(spec=AbstractProvider),
        secret_provider=Mock(spec=SecretProvider),
        vars_config=Mock(spec=VariableConfig),
        helm_config=Mock(spec=HelmConfig),
    )

    monkeypatch.setattr(project, "environments", ["environment_name"])
    actual_result = project.select_environment(name="environment_name")

    return Fixture(
        actual_result=actual_result,
        mock_load_environment=mock_load_environment,
        project=project,
    )


def test_select_environment_calls_load_environment(setup: Fixture):
    setup.mock_load_environment.assert_called_once_with(environment_name="environment_name", project=setup.project)


def test_should_return_the_environment(setup: Fixture):
    assert setup.actual_result == setup.mock_load_environment.return_value


class ProjectTests(TestCase):
    def setUp(self) -> None:
        self.project = create_mock_project()

    @mock.patch("strong_opx.project.base.shell")
    def test_git_revision_hash(self, shell_mock: mock.Mock):
        shell_mock.return_value.stdout.decode.return_value = "something"
        self.assertEqual(Project.git_revision_hash(self.project), "something")

        shell_mock.assert_called_with(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            cwd=self.project.path,
        )

    @mock.patch("strong_opx.project.base.shell")
    def test_git_revision_hash__invalid_dir(self, shell_mock: mock.Mock):
        def raise_process_error(*args, **kwargs):
            raise ProcessError()

        shell_mock.side_effect = raise_process_error
        self.assertEqual(Project.git_revision_hash(self.project), None)
        shell_mock.assert_called_once()
