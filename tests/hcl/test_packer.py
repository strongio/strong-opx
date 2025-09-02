import os
from unittest import TestCase, mock

from strong_opx.hcl import run_packer
from tests.mocks import create_mock_environment, create_mock_project


@mock.patch.dict(os.environ, {}, clear=True)
class RunPackerTest(TestCase):
    def setUp(self) -> None:
        self.project = create_mock_project()
        self.environment = create_mock_environment(project=self.project)
        self.project.config = mock.Mock(packer_executable="packer")

    @mock.patch("strong_opx.hcl.runner.shell")
    @mock.patch("strong_opx.hcl.packer.PackerRunner.extract_vars")
    def test_pass_additional_args(self, extract_vars_mock: mock.Mock, shell_mock: mock.Mock):
        extract_vars_mock.return_value = {}

        run_packer(self.environment, "init", "-upgrade")
        shell_mock.assert_called_once_with(
            ("packer", "init", "-upgrade"),
            env={"PKR_PLUGIN_PATH": os.path.join(self.project.path, ".packer")},
            cwd=os.path.join(self.project.path, "packer"),
        )
