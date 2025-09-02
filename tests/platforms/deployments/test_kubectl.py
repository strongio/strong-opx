from dataclasses import dataclass
from subprocess import CompletedProcess
from unittest.mock import Mock, call, patch

import pytest

from strong_opx.platforms import Platform
from strong_opx.platforms.deployments import KubeCtlDeploymentProvider
from strong_opx.platforms.deployments.kubectl import DeploymentStatus, DeploymentSummary
from strong_opx.project import Environment, Project


class TestKubeCtlDeploymentProvider:
    @dataclass
    class Fixture:
        mock_kubectl: Mock
        expected_kubectl_calls: list
        expected_load_all_calls: list
        mock_yaml: Mock

    @dataclass
    class Params:
        expected_kubectl_calls: list
        configs: list
        expected_load_all_calls: list
        yaml_load_all: dict
        deployment_status: DeploymentStatus

    @pytest.fixture(
        ids=[
            "deployment configured",
            "deployment unchanged",
            "deployment bar namespace",
            "statefulset",
            "statefulset unchanged",
        ],
        params=[
            Params(
                expected_kubectl_calls=[
                    call("apply", "-f", "someDirectory", stdout=-1),
                    call("rollout", "status", "deployment", "foo", "-n", "default"),
                ],
                deployment_status=DeploymentStatus("deployment", "foo", "configured"),
                expected_load_all_calls=[call("someDirectory/someFile.yml")],
                configs=["someFile.yml"],
                yaml_load_all={"metadata": {"name": "foo"}, "kind": "deployment"},
            ),
            Params(
                expected_kubectl_calls=[
                    call("apply", "-f", "someDirectory", stdout=-1),
                    call("rollout", "status", "deployment", "foo", "-n", "default"),
                    call("rollout", "restart", "deployment", "foo", "-n", "default"),
                    call("rollout", "status", "deployment", "foo", "-n", "default"),
                ],
                deployment_status=DeploymentStatus("deployment", "foo", "unchanged"),
                expected_load_all_calls=[call("someDirectory/someFile.yml")],
                configs=["someFile.yml"],
                yaml_load_all={"metadata": {"name": "foo"}, "kind": "deployment"},
            ),
            Params(
                expected_kubectl_calls=[
                    call("apply", "-f", "someDirectory", stdout=-1),
                    call("rollout", "status", "deployment", "foo", "-n", "bar"),
                ],
                deployment_status=DeploymentStatus("deployment", "foo", "configured"),
                expected_load_all_calls=[call("someDirectory/someFile.yml")],
                configs=["someFile.yml"],
                yaml_load_all={"metadata": {"name": "foo", "namespace": "bar"}, "kind": "deployment"},
            ),
            Params(
                expected_kubectl_calls=[
                    call("apply", "-f", "someDirectory", stdout=-1),
                    call("rollout", "status", "statefulset", "foo", "-n", "default"),
                ],
                deployment_status=DeploymentStatus("statefulset", "foo", "configured"),
                expected_load_all_calls=[call("someDirectory/someFile.yml")],
                configs=["someFile.yml"],
                yaml_load_all={"metadata": {"name": "foo"}, "kind": "statefulset"},
            ),
            Params(
                expected_kubectl_calls=[
                    call("apply", "-f", "someDirectory", stdout=-1),
                    call("rollout", "status", "statefulset", "foo", "-n", "default"),
                ],
                deployment_status=DeploymentStatus("statefulset", "foo", "unchanged"),
                expected_load_all_calls=[call("someDirectory/someFile.yml")],
                configs=["someFile.yml"],
                yaml_load_all={"metadata": {"name": "foo"}, "kind": "statefulset"},
            ),
        ],
    )
    @patch("strong_opx.platforms.deployments.kubectl.yaml", autospec=True)
    @patch("os.listdir", autospec=True)
    @patch.object(DeploymentSummary, "parse")
    def setup(self, mock_parse_deployment_summary, mock_listdir, mock_yaml, request):
        mock_project = Mock(spec=Project)
        mock_kubectl = Mock()
        mock_kubectl.return_value = CompletedProcess((), 0, stdout=b"")

        mock_environment = Mock(spec=Environment)
        mock_platform = Mock(spec=Platform)
        mock_platform.kubectl = mock_kubectl
        mock_yaml.load_all.return_value = [request.param.yaml_load_all]

        mock_parse_deployment_summary.return_value = DeploymentSummary()
        mock_parse_deployment_summary.return_value.lines.append(request.param.deployment_status)

        mock_listdir.return_value = request.param.configs

        KubeCtlDeploymentProvider(project=mock_project, environment=mock_environment, platform=mock_platform).deploy(
            node="unused", manifest_directory="someDirectory"
        )

        return TestKubeCtlDeploymentProvider.Fixture(
            mock_kubectl=mock_kubectl,
            expected_kubectl_calls=request.param.expected_kubectl_calls,
            expected_load_all_calls=request.param.expected_load_all_calls,
            mock_yaml=mock_yaml,
        )

    def test_yaml_load_all_called(self, setup: Fixture):
        setup.mock_yaml.load_all.assert_has_calls(
            setup.expected_load_all_calls,
            any_order=True,
        )

    def test_kubectl_expected_calls(self, setup: Fixture):
        assert setup.mock_kubectl.mock_calls == setup.expected_kubectl_calls
