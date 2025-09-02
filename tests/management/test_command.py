import argparse
import os
from unittest import TestCase, mock

from strong_opx.management.command import BaseCommand, ProjectCommand
from strong_opx.project import Project
from tests.mocks import create_mock_project


class BaseCommandTests(TestCase):
    @mock.patch.object(BaseCommand, "handle")
    def test_allow_additional_args(self, handle_mock: mock.Mock):
        command = BaseCommand()
        command.allow_additional_args = True
        command.run_from_argv(["strong-opx", "command", "--", "some-value", "--something-else"])

        handle_mock.assert_called_once_with(
            verbosity=2, traceback=False, additional_args=("some-value", "--something-else")
        )

    @mock.patch.object(BaseCommand, "handle")
    def test_allow_additional_args_but_multiple_delimiters(self, handle_mock: mock.Mock):
        command = BaseCommand()
        command.allow_additional_args = True
        command.run_from_argv(["strong-opx", "command", "--", "some-value", "--", "something-else"])

        handle_mock.assert_called_once_with(
            verbosity=2, traceback=False, additional_args=("some-value", "--", "something-else")
        )

    @mock.patch.object(BaseCommand, "handle")
    def test_allow_additional_args_and_parse_known_args_only(self, handle_mock: mock.Mock):
        command = BaseCommand()
        command.allow_additional_args = True
        command.parse_known_args = True
        command.run_from_argv(["strong-opx", "command", "unknown-value", "--", "some-value", "--something-else"])

        handle_mock.assert_called_once_with(
            verbosity=2, traceback=False, additional_args=("unknown-value", "some-value", "--something-else")
        )


class ProjectCommandTests(TestCase):
    @mock.patch("strong_opx.management.command.validate_project_name")
    def test_add_arguments(self, validate_project_name_mock: mock.Mock):
        validate_project_name_mock.side_effect = lambda x: x

        arg_parser = argparse.ArgumentParser()
        ProjectCommand().add_arguments(arg_parser)

        actual_parsed_args: dict = vars(arg_parser.parse_args(["--project", "some-project", "--env", "some-env"]))

        self.assertDictEqual(actual_parsed_args, {"project": "some-project", "environment": "some-env"})

    @mock.patch.object(Project, "from_name", mock.Mock(return_value=create_mock_project(environments=["env1", "env2"])))
    @mock.patch("strong_opx.management.utils.system_config", mock.Mock(registered_projects=["project1", "project2"]))
    @mock.patch("strong_opx.management.utils.select_prompt")
    def test_ask_for_project_and_env(self, select_prompt_mock: mock.Mock):
        select_prompt_mock.side_effect = ["project", "environment"]
        options = ProjectCommand().transform_args(argparse.Namespace(), [])

        select_prompt_mock.assert_has_calls(
            (
                mock.call("Select Project", ["project1", "project2"]),
                mock.call("Select Environment", ["env1", "env2"]),
            )
        )

        self.assertIn("project", options)
        self.assertIn("environment", options)

    @mock.patch.object(Project, "from_name", mock.Mock(return_value=create_mock_project(environments=["env1"])))
    @mock.patch("strong_opx.management.utils.system_config", mock.Mock(registered_projects=["project1", "project2"]))
    @mock.patch("strong_opx.management.utils.select_prompt")
    def test_ask_for_project_only_if_single_env(self, select_prompt_mock: mock.Mock):
        select_prompt_mock.side_effect = "project"
        options = ProjectCommand().transform_args(argparse.Namespace(), [])

        select_prompt_mock.assert_called_once_with("Select Project", ["project1", "project2"])
        options["project"].select_environment.assert_called_once_with(name="env1")

    @mock.patch.object(Project, "from_name", mock.Mock(return_value=create_mock_project(environments=["env1", "env2"])))
    @mock.patch("strong_opx.management.utils.system_config", mock.Mock(registered_projects=["project1", "project2"]))
    @mock.patch("strong_opx.management.utils.select_prompt")
    def test_ask_for_project_only_if_env_is_specified(self, select_prompt_mock: mock.Mock):
        select_prompt_mock.return_value = "project"
        options = ProjectCommand().transform_args(argparse.Namespace(environment="env2"), [])

        select_prompt_mock.assert_called_once_with("Select Project", ["project1", "project2"])
        options["project"].select_environment.assert_called_once_with(name="env2")

    @mock.patch.object(Project, "from_name", mock.Mock(return_value=create_mock_project(environments=["env1", "env2"])))
    @mock.patch("strong_opx.management.utils.system_config", mock.Mock(registered_projects=["project1", "project2"]))
    @mock.patch("strong_opx.management.utils.select_prompt")
    def test_ask_for_env_only_if_project_is_specified(self, select_prompt_mock: mock.Mock):
        select_prompt_mock.return_value = "environment"
        options = ProjectCommand().transform_args(argparse.Namespace(project="project1"), [])

        select_prompt_mock.assert_called_once_with("Select Environment", ["env1", "env2"])
        options["project"].select_environment.assert_called_once_with(name="environment")

    @mock.patch.object(Project, "from_name", mock.Mock(return_value=create_mock_project(environments=["env1"])))
    @mock.patch("strong_opx.management.utils.system_config", mock.Mock(registered_projects=["project1", "project2"]))
    @mock.patch("strong_opx.management.utils.get_current_project", mock.Mock(return_value="project1"))
    def test_pick_project_from_current_dir(self):
        options = ProjectCommand().transform_args(argparse.Namespace(project="project1"), [])
        options["project"].select_environment.assert_called_once_with(name="env1")

    @mock.patch.object(Project, "from_name")
    @mock.patch("strong_opx.management.utils.system_config", mock.Mock(registered_projects=["project1", "project2"]))
    @mock.patch.dict(
        os.environ,
        {
            "STRONG_OPX_PROJECT": "project1",
            "STRONG_OPX_ENVIRONMENT": "env2",
        },
        clear=True,
    )
    def test_load_from_env(self, project_from_name_mock: mock.Mock):
        project_from_name_mock.return_value = create_mock_project(environments=["env1", "env2"])

        options = ProjectCommand().transform_args(argparse.Namespace(), [])
        project_from_name_mock.assert_called_once_with("project1")
        options["project"].select_environment.assert_called_once_with(name="env2")
