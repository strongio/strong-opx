import os
from unittest import TestCase, mock

from strong_opx.exceptions import UndefinedVariableError
from strong_opx.hcl.runner import HCLRunner
from strong_opx.template import Context
from tests.helper_functions import assert_has_calls_exactly, patch_colorama
from tests.mocks import create_mock_environment, create_mock_project


class TestHCLRunner(HCLRunner):
    extension = ".tf"
    env_var_prefix = "T"

    def __init__(self):
        project = create_mock_project()
        environment = create_mock_environment(project=project)
        super().__init__(environment=environment, directory=environment.project.path)

    def get_executable(self) -> str:
        return "aExecutable"


@patch_colorama
class HCLRunnerTest(TestCase):
    @mock.patch("strong_opx.hcl.runner.os.listdir")
    @mock.patch("strong_opx.hcl.runner.open")
    @mock.patch("strong_opx.hcl.runner.HCLVariableExtractor")
    def test_variable_extraction_only_from_whitelisted_files(
        self, extractor_mock: mock.Mock, open_mock: mock.Mock, listdir_mock: mock.Mock
    ):
        listdir_mock.return_value = ["some-file.txt", "config.yml", "main.tf", "output.tf"]
        open_mock.return_value.__enter__.side_effect = ["file-1", "file-2"]

        runner = TestHCLRunner()
        runner.extract_vars()

        open_mock.assert_has_calls(
            [
                mock.call(os.path.join(runner.environment.project.path, "main.tf")),
                mock.call(os.path.join(runner.environment.project.path, "output.tf")),
            ],
            any_order=True,
        )

        assert_has_calls_exactly(
            mock=extractor_mock.return_value.extract,
            expected_calls=[
                mock.call("/tmp/unittest/main.tf", "file-1"),
                mock.call("/tmp/unittest/output.tf", "file-2"),
            ],
        )

    @mock.patch("strong_opx.hcl.runner.os.listdir")
    @mock.patch("strong_opx.hcl.runner.HCLVariableExtractor")
    def test_required_and_optional_vars_with_none_missing(self, extractor_mock: mock.Mock, listdir_mock: mock.Mock):
        listdir_mock.return_value = []
        extractor_mock.return_value.required_vars = ["VAR_1", "VAR_2"]
        extractor_mock.return_value.optional_vars = ["VAR_3"]

        runner = TestHCLRunner()
        runner.environment.context = Context({"VAR_1": "VAL_1", "VAR_2": "VAL_2", "VAR_3": "VAL_3"})

        actual_result = runner.extract_vars()

        self.assertDictEqual({"T_VAR_1": "VAL_1", "T_VAR_2": "VAL_2", "T_VAR_3": "VAL_3"}, actual_result)

    @mock.patch("strong_opx.hcl.runner.os.listdir")
    @mock.patch("strong_opx.hcl.runner.HCLVariableExtractor")
    def test_missing_required_vars(self, extractor_mock: mock.Mock, listdir_mock: mock.Mock):
        listdir_mock.return_value = []
        extractor_mock.return_value.required_vars = ["VAR_1", "VAR_2"]

        runner = TestHCLRunner()
        runner.environment.context = Context()

        with self.assertRaises(UndefinedVariableError) as cm:
            runner.extract_vars()

        self.assertEqual(
            str(cm.exception),
            "\n"
            "{Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}VAR_1 is undefined{Style.RESET_ALL}\n"
            "{Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}VAR_2 is undefined{Style.RESET_ALL}",
        )

    @mock.patch("strong_opx.hcl.runner.os.listdir")
    @mock.patch("strong_opx.hcl.runner.HCLVariableExtractor")
    def test_missing_optional_vars(self, extractor_mock: mock.Mock, listdir_mock: mock.Mock):
        listdir_mock.return_value = []
        extractor_mock.return_value.optional_vars = {"VAR_1", "VAR_2"}

        runner = TestHCLRunner()
        runner.environment.context = Context()

        # No exception should be raised
        runner.extract_vars()
