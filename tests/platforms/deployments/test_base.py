import os.path
from unittest import TestCase, mock

from parameterized import parameterized

from strong_opx.platforms.deployments.base import ConfigDeploymentProvider, DeploymentProvider, NodeConfig
from strong_opx.template import Context
from tests.mocks import create_mock_environment, create_mock_project


class DeploymentProviderTests(TestCase):
    def test_select_nodes(self):
        provider = mock.MagicMock(spec=DeploymentProvider)
        provider.name = "some-provider"
        nodes = DeploymentProvider.select_nodes(
            provider,
            [
                "some-provider/node1",
                "some-provider/node2",
                "another-provider/node1",
                "another-provider/node2",
            ],
        )

        self.assertListEqual(
            nodes,
            [
                "some-provider/node1",
                "some-provider/node2",
            ],
        )


class ConfigDeploymentProviderTests(TestCase):
    def setUp(self) -> None:
        self.context = Context({"VAR1": "1", "VAR2": "2"})
        self.project = create_mock_project()
        self.environment = create_mock_environment(context=self.context, project=self.project)
        self.provider = mock.MagicMock(
            project=self.project,
            environment=self.environment,
            spec=ConfigDeploymentProvider,
        )
        self.provider.name = "some-provider"

    @parameterized.expand(
        [
            [(".foo", ".bar"), "someFile.foo", True],
            [(".banana", ".taco"), "someFile.foo", False],
            [(".foo", ".bar"), "someFile.unittest.foo", True],
            [(".foo", ".bar"), "someFile.someOtherEnvionmentName.foo", False],
        ]
    )
    def test_is_config_applicable(self, allowed_extensions, file_name, expected):
        provider = mock.MagicMock(
            spec=ConfigDeploymentProvider, allowed_extensions=allowed_extensions, environment=self.environment
        )
        self.assertEqual(ConfigDeploymentProvider.is_config_applicable(provider, file_name), expected)

    @mock.patch("os.path.exists", mock.MagicMock(return_value=True))
    def test_select_nodes__from_project(self):
        provider = mock.MagicMock(spec=ConfigDeploymentProvider, project=create_mock_project())
        provider.name = "some-provider"

        nodes = ConfigDeploymentProvider.select_nodes(
            provider, ["some-provider/some-node", "another-provider/some-node"]
        )
        self.assertListEqual(nodes, ["some-provider/some-node"])
        self.assertEqual(nodes[0].path, "/tmp/unittest/some-provider/some-node")

    @mock.patch("os.path.exists", mock.MagicMock(return_value=True))
    def test_select_nodes__absolute_path(self):
        provider = mock.MagicMock(spec=ConfigDeploymentProvider, project=create_mock_project())
        provider.name = "some-provider"

        nodes = ConfigDeploymentProvider.select_nodes(
            provider, ["some-provider:/tmp/some-node", "another-provider/some-node"]
        )
        self.assertListEqual(nodes, ["some-provider:/tmp/some-node"])
        self.assertEqual(nodes[0].path, "/tmp/some-node")

    def assertDeployCall(self, cl: mock.call, node: NodeConfig, files: list[str]):
        c_node, c_dir = cl.args
        self.assertEqual(c_node, node)

    @mock.patch("os.path.isdir", mock.MagicMock(return_value=False))
    @mock.patch("strong_opx.platforms.deployments.base.FileTemplate", mock.MagicMock())
    def test_deploy__file(self):
        node = NodeConfig("some-provider/some-file.yml", "/tmp/some-file.yml")
        ConfigDeploymentProvider.deploy_node(self.provider, node)
        self.assertDeployCall(self.provider.deploy.call_args, node, ["some-file.yml"])

    @mock.patch("os.path.isdir", mock.MagicMock(return_value=True))
    @mock.patch("os.listdir", mock.MagicMock(return_value=["one.yml", "two.yml"]))
    @mock.patch("strong_opx.platforms.deployments.base.FileTemplate", mock.MagicMock())
    def test_deploy__directory(self):
        node = NodeConfig("some-provider/some-directory", "/tmp/some-directory")
        ConfigDeploymentProvider.deploy_node(self.provider, node)
        self.assertDeployCall(self.provider.deploy.call_args, node, ["one.yml", "two.yml"])

    @mock.patch("os.path.isdir", mock.MagicMock(return_value=True))
    @mock.patch("os.listdir", mock.MagicMock(return_value=["one.env1.yml", "two.env1.yml"]))
    @mock.patch("strong_opx.platforms.deployments.base.FileTemplate", mock.MagicMock())
    def test_deploy__directory_but_different_env(self):
        self.provider.is_config_applicable.return_value = False

        node = NodeConfig("some-provider/some-directory", "/tmp/some-directory")
        self.assertFalse(ConfigDeploymentProvider.deploy_node(self.provider, node))
        self.provider.deploy.assert_not_called()

    @mock.patch("tempfile.TemporaryDirectory")
    @mock.patch("strong_opx.platforms.deployments.base.FileTemplate")
    @mock.patch("os.path.isdir", mock.MagicMock(return_value=False))
    def test_deploy__file_template_is_used(self, file_template_mock: mock.Mock, temp_dir_mock: mock.Mock):
        temp_dir_mock.return_value.__enter__.return_value = "/tmp/some-directory"

        node = NodeConfig("some-provider/some-file.yml", "/tmp/some-file.yml")
        ConfigDeploymentProvider.deploy_node(self.provider, node)
        self.assertDeployCall(self.provider.deploy.call_args, node, ["some-file.yml"])

        file_template_mock.assert_called_once_with("/tmp/some-file.yml")
        file_template_mock.return_value.render_to_file.assert_called_once_with(
            "/tmp/some-directory/some-file.yml", self.context
        )
