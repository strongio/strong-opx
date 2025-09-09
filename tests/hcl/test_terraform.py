import os
from unittest import TestCase, mock

from strong_opx.exceptions import ImproperlyConfiguredError
from strong_opx.hcl import run_terraform
from tests.mocks import create_mock_environment, create_mock_project


@mock.patch.dict(os.environ, {}, clear=True)
class RunTerraformTests(TestCase):
    def setUp(self) -> None:
        self.project = create_mock_project()
        self.environment = create_mock_environment(project=self.project)
        self.project.config = mock.Mock(terraform_executable="terraform")

    @mock.patch("strong_opx.hcl.runner.shell")
    @mock.patch("strong_opx.hcl.runner.os.path.exists", new=mock.MagicMock(return_value=True))
    @mock.patch("strong_opx.hcl.runner.os.listdir", new=mock.MagicMock(return_value=[".tfbackend"]))
    @mock.patch("strong_opx.hcl.terraform.TerraformRunner.extract_vars", new=mock.MagicMock(return_value={}))
    def test_pass_additional_args(self, shell_mock: mock.Mock):
        run_terraform(self.environment, "apply", "-target", "hello")
        shell_mock.assert_called_once()
        self.assertTupleEqual(shell_mock.call_args[0][0], ("terraform", "apply", "-target", "hello"))

    @mock.patch("strong_opx.hcl.runner.shell")
    @mock.patch("strong_opx.hcl.terraform.os.path.exists", new=mock.MagicMock(return_value=True))
    @mock.patch("strong_opx.hcl.terraform.TerraformRunner.extract_vars", new=mock.MagicMock(return_value={}))
    @mock.patch("strong_opx.hcl.runner.os.listdir", new=mock.MagicMock(return_value=["s3.tfbackend"]))
    def test_backend_config_for_init(self, shell_mock: mock.Mock):
        run_terraform(self.environment, "init")
        backend_config_path = os.path.join(self.environment.path, "s3.tfbackend")
        shell_mock.assert_called_once_with(
            ("terraform", "init", f"-backend-config={backend_config_path}"),
            env={"TF_DATA_DIR": os.path.join(self.environment.path, ".terraform")},
            cwd=os.path.join(self.project.path, "terraform"),
        )

    @mock.patch("strong_opx.hcl.runner.shell")
    @mock.patch("strong_opx.hcl.terraform.os.path.exists", new=mock.MagicMock(return_value=True))
    @mock.patch("strong_opx.hcl.terraform.TerraformRunner.extract_vars", new=mock.MagicMock(return_value={}))
    @mock.patch("strong_opx.hcl.runner.os.listdir", new=mock.MagicMock(return_value=[".tfbackend"]))
    def test_backend_config_for_non_init(self, shell_mock: mock.Mock):
        run_terraform(self.environment, "apply")
        shell_mock.assert_called_once_with(
            ("terraform", "apply"),
            env={"TF_DATA_DIR": os.path.join(self.environment.path, ".terraform")},
            cwd=os.path.join(self.project.path, "terraform"),
        )

    @mock.patch("strong_opx.hcl.runner.shell", new=mock.MagicMock())
    @mock.patch("strong_opx.hcl.terraform.os.path.exists", new=mock.MagicMock(return_value=False))
    @mock.patch("strong_opx.hcl.terraform.TerraformRunner.extract_vars", new=mock.MagicMock(return_value={}))
    @mock.patch("strong_opx.hcl.runner.os.listdir", new=mock.MagicMock(return_value=[".tfbackend"]))
    def test_backend_config_for_non_init__uninitialized(self):
        with self.assertRaises(ImproperlyConfiguredError) as cm:
            run_terraform(self.environment, "apply")

        self.assertEqual(
            str(cm.exception), "Please run `strong-opx terraform init` prior to running other Terraform commands."
        )

    @mock.patch("strong_opx.hcl.runner.shell", new=mock.MagicMock())
    @mock.patch("strong_opx.hcl.terraform.TerraformRunner.extract_vars", new=mock.MagicMock(return_value={}))
    @mock.patch("strong_opx.hcl.runner.os.listdir", new=mock.MagicMock(return_value=[]))
    def test_no_backend_file(self):
        with self.assertRaises(ImproperlyConfiguredError) as cm:
            run_terraform(self.environment, "apply")

        self.assertEqual(
            str(cm.exception),
            "No backend configuration file found. Please create a .tfbackend file in the environment directory.",
        )

    @mock.patch("strong_opx.hcl.runner.shell", new=mock.MagicMock())
    @mock.patch("strong_opx.hcl.terraform.TerraformRunner.extract_vars", new=mock.MagicMock(return_value={}))
    @mock.patch("strong_opx.hcl.runner.os.listdir", new=mock.MagicMock(return_value=["a.tfbackend", "b.tfbackend"]))
    def test_multiple_backend_file(self):
        with self.assertRaises(ImproperlyConfiguredError) as cm:
            run_terraform(self.environment, "apply")

        self.assertEqual(
            str(cm.exception),
            "Multiple backend configuration files found. Please ensure there is only one .tfbackend "
            "file in the environment directory.",
        )
