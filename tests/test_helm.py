import os.path
from subprocess import CompletedProcess
from unittest import TestCase, mock

from pydantic import ValidationError

from strong_opx.exceptions import HelmError
from strong_opx.helm import HelmChart, HelmChartQualifiedName, HelmConfig, HelmManager
from tests.mocks import create_mock_environment, create_mock_kubernetes_platform, create_mock_project


class HelmChartTests(TestCase):
    def test_qualified_name(self):
        chart = HelmChart(repo="some-repo", chart="chart-a")
        self.assertEqual(chart.qualified_name, "default:chart-a")

    def test_qualified_name_custom_namespace(self):
        chart = HelmChart(repo="some-repo", chart="chart-b", namespace="some-ns")
        self.assertEqual(chart.qualified_name, "some-ns:chart-b")

    def test_name_equal_chart_if_missing(self):
        chart = HelmChart(repo="some-repo", chart="chart-c")
        self.assertEqual(chart.name, "chart-c")

    def test_specified_name(self):
        chart = HelmChart(repo="some-repo", chart="chart-c", name="chart-c-name")
        self.assertEqual(chart.name, "chart-c-name")


class HelmConfigTests(TestCase):
    def test_default_repos(self):
        config = HelmConfig()
        self.assertDictEqual(config.repos, {"stable": "https://charts.helm.sh/stable"})

    def test_default_repo_if_not_specified(self):
        config = HelmConfig(repos={"some-repo": "https://charts.example.com"})
        self.assertDictEqual(
            config.repos, {"some-repo": "https://charts.example.com/", "stable": "https://charts.helm.sh/stable"}
        )

    def test_invalid_repo_url(self):
        with self.assertRaises(ValidationError):
            HelmConfig(repos={"some-repo": "charts.example.com"})


class HelmManagerTests(TestCase):
    helm_run: mock.Mock

    def create_helm_manager(
        self, helm_config: HelmConfig, installed_helm_charts: list[HelmChartQualifiedName] = None
    ) -> HelmManager:
        project = create_mock_project(helm_config=helm_config)
        environment = create_mock_environment(project=project)
        platform = create_mock_kubernetes_platform(project=project, environment=environment)

        manager = HelmManager(platform)
        if installed_helm_charts is not None:
            manager.__dict__["installed_helm_charts"] = installed_helm_charts
        self.helm_run = manager.run = mock.MagicMock()
        return manager

    def test_installed_helm_charts(self):
        helm_manager = self.create_helm_manager(HelmConfig(charts=[]))

        self.helm_run.return_value = mock.create_autospec(
            spec=CompletedProcess,
            instance=True,
            stdout=b'[{"namespace": "default", "name": "milena"},{"namespace": "keda", "name": "ivan"}]',
        )

        self.assertListEqual(
            helm_manager.installed_helm_charts,
            [
                HelmChartQualifiedName("default", "milena"),
                HelmChartQualifiedName("keda", "ivan"),
            ],
        )

    def test_install(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(charts=[HelmChart(repo="stable", chart="chart-1")]), installed_helm_charts=[]
        )

        helm_manager.apply(charts=[], upgrade=False)
        self.helm_run.assert_called_once_with(
            "install",
            "chart-1",
            "chart-1",
            "--repo",
            "https://charts.helm.sh/stable",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "5m0s",
        )

    def test_install_oci_repo(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(
                charts=[HelmChart(repo="fake-oci-repo", chart="chart-1")],
                repos={"fake-oci-repo": "oci://fake-oci-repo"},
            ),
            installed_helm_charts=[],
        )

        helm_manager.apply(charts=[], upgrade=False)
        self.helm_run.assert_called_once_with(
            "install",
            "chart-1",
            "oci://fake-oci-repo",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "5m0s",
        )

    def test_install_custom_timeout(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(charts=[HelmChart(repo="stable", chart="chart-1", timeout="20 years")]), installed_helm_charts=[]
        )

        helm_manager.apply(charts=[], upgrade=False)
        self.helm_run.assert_called_once_with(
            "install",
            "chart-1",
            "chart-1",
            "--repo",
            "https://charts.helm.sh/stable",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "20 years",
        )

    def test_install__additional_args(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(charts=[HelmChart(repo="stable", chart="chart-1")]), installed_helm_charts=[]
        )
        helm_manager.apply(upgrade=False, additional_args=("--debug",))
        self.helm_run.assert_called_once_with(
            "install",
            "chart-1",
            "chart-1",
            "--repo",
            "https://charts.helm.sh/stable",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "5m0s",
            "--debug",
        )

    def test_install__specific_version(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(charts=[HelmChart(repo="stable", chart="chart-1", version="0.1")]), installed_helm_charts=[]
        )
        helm_manager.apply(upgrade=False)
        self.helm_run.assert_called_once_with(
            "install",
            "chart-1",
            "chart-1",
            "--repo",
            "https://charts.helm.sh/stable",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "5m0s",
            "--version",
            "0.1",
        )

    def test_install__specific_chart(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(
                charts=[
                    HelmChart(repo="stable", chart="chart-1"),
                    HelmChart(repo="stable", chart="chart-2"),
                ]
            ),
            installed_helm_charts=[],
        )
        helm_manager.apply(charts=["chart-1"], upgrade=False)
        self.helm_run.assert_called_once_with(
            "install",
            "chart-1",
            "chart-1",
            "--repo",
            "https://charts.helm.sh/stable",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "5m0s",
        )

    def test_install__skip_already_installed(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(
                charts=[
                    HelmChart(repo="stable", chart="chart-1"),
                    HelmChart(repo="stable", chart="chart-2"),
                ]
            ),
            installed_helm_charts=[HelmChartQualifiedName("default", "chart-1")],
        )
        helm_manager.apply(upgrade=False)
        self.helm_run.assert_called_once_with(
            "install",
            "chart-2",
            "chart-2",
            "--repo",
            "https://charts.helm.sh/stable",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "5m0s",
        )

    def test_install__missing_custom_values(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(charts=[HelmChart(repo="stable", chart="chart-1", values="helm/custom-values.yml")]),
            installed_helm_charts=[],
        )

        with self.assertRaises(HelmError):
            helm_manager.apply(upgrade=False)

        self.helm_run.assert_not_called()

    def test_upgrade(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(charts=[HelmChart(repo="stable", chart="chart-1")]), installed_helm_charts=[]
        )
        helm_manager.apply(upgrade=True)
        self.helm_run.assert_called_once_with(
            "upgrade",
            "--install",
            "chart-1",
            "chart-1",
            "--repo",
            "https://charts.helm.sh/stable",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "5m0s",
        )

    def test_upgrade__specific_version(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(charts=[HelmChart(repo="stable", chart="chart-1", version="0.1")]), installed_helm_charts=[]
        )
        helm_manager.apply(upgrade=True)
        self.helm_run.assert_called_once_with(
            "upgrade",
            "--install",
            "chart-1",
            "chart-1",
            "--repo",
            "https://charts.helm.sh/stable",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "5m0s",
            "--version",
            "0.1",
        )

    def test_upgrade__specific_chart(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(
                charts=[
                    HelmChart(repo="stable", chart="chart-1"),
                    HelmChart(repo="stable", chart="chart-2"),
                ]
            ),
            installed_helm_charts=[],
        )
        helm_manager.apply(charts=["chart-1"], upgrade=True)
        self.helm_run.assert_called_once_with(
            "upgrade",
            "--install",
            "chart-1",
            "chart-1",
            "--repo",
            "https://charts.helm.sh/stable",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "5m0s",
        )

    @mock.patch("strong_opx.helm.os.path.exists")
    @mock.patch("strong_opx.helm.FileTemplate", new=mock.MagicMock())
    @mock.patch("strong_opx.helm.tempfile.NamedTemporaryFile")
    def test_install_custom_values(self, named_temporary_file_mock: mock.Mock, path_exists_mock: mock.Mock):
        path_exists_mock.return_value = True
        named_temporary_file_mock.return_value.__enter__.return_value.name = "values-file.yml"

        helm_manager = self.create_helm_manager(
            HelmConfig(charts=[HelmChart(repo="stable", chart="chart-1", values="helm/chart.yml")]),
            installed_helm_charts=[],
        )

        helm_manager.apply(upgrade=False)
        self.helm_run.assert_called_once_with(
            "install",
            "chart-1",
            "chart-1",
            "--repo",
            "https://charts.helm.sh/stable",
            "-n",
            "default",
            "--create-namespace",
            "--wait",
            "--timeout",
            "5m0s",
            "--values",
            "values-file.yml",
        )

    @mock.patch("strong_opx.helm.os.path.exists")
    @mock.patch("strong_opx.helm.FileTemplate")
    @mock.patch("strong_opx.helm.tempfile.NamedTemporaryFile")
    def test_install_custom_values_rendering(
        self, named_temporary_file_mock: mock.Mock, file_template_mock: mock.Mock, path_exists_mock: mock.Mock
    ):
        path_exists_mock.return_value = True
        named_temporary_file_mock.return_value.__enter__.return_value.name = "values-tmp-file.yml"

        helm_manager = self.create_helm_manager(
            HelmConfig(charts=[HelmChart(repo="stable", chart="chart-1", values="helm/chart.yml")]),
            installed_helm_charts=[],
        )

        helm_manager.apply(upgrade=False)
        file_template_mock.assert_called_once_with(os.path.join(helm_manager.platform.project.path, "helm/chart.yml"))
        file_template_mock.return_value.render_to_file.assert_called_once_with(
            "values-tmp-file.yml", helm_manager.platform.environment.context
        )

    def test_upgrade__upgrade_already_installed(self):
        helm_manager = self.create_helm_manager(
            HelmConfig(
                charts=[
                    HelmChart(repo="stable", chart="chart-1"),
                    HelmChart(repo="stable", chart="chart-2"),
                ]
            ),
            installed_helm_charts=[HelmChartQualifiedName("default", "chart-1")],
        )
        helm_manager.apply(upgrade=True)
        self.helm_run.assert_has_calls(
            [
                mock.call(
                    "upgrade",
                    "--install",
                    "chart-1",
                    "chart-1",
                    "--repo",
                    "https://charts.helm.sh/stable",
                    "-n",
                    "default",
                    "--create-namespace",
                    "--wait",
                    "--timeout",
                    "5m0s",
                ),
                mock.call(
                    "upgrade",
                    "--install",
                    "chart-2",
                    "chart-2",
                    "--repo",
                    "https://charts.helm.sh/stable",
                    "-n",
                    "default",
                    "--create-namespace",
                    "--wait",
                    "--timeout",
                    "5m0s",
                ),
            ],
            any_order=True,
        )

    @mock.patch("strong_opx.helm.input_boolean")
    def test_prune__nothing(self, input_boolean_mock: mock.Mock):
        input_boolean_mock.return_value = True

        helm_manager = self.create_helm_manager(
            HelmConfig(
                charts=[
                    HelmChart(repo="stable", chart="chart-1"),
                    HelmChart(repo="stable", chart="chart-2"),
                ]
            ),
            installed_helm_charts=[HelmChartQualifiedName("default", "chart-1")],
        )

        helm_manager.prune()
        self.helm_run.assert_not_called()

    @mock.patch("strong_opx.helm.input_boolean")
    def test_prune__chart(self, input_boolean_mock: mock.Mock):
        input_boolean_mock.return_value = True
        helm_manager = self.create_helm_manager(
            HelmConfig(
                charts=[
                    HelmChart(repo="stable", chart="chart-1"),
                    HelmChart(repo="stable", chart="chart-2"),
                ]
            ),
            installed_helm_charts=[
                HelmChartQualifiedName("default", "chart-2"),
                HelmChartQualifiedName("default", "chart-3"),
            ],
        )
        helm_manager.prune()
        self.helm_run.assert_called_once_with("uninstall", "chart-3", "-n", "default")

    @mock.patch("strong_opx.helm.input_boolean")
    def test_prune__additional_args(self, input_boolean_mock: mock.Mock):
        input_boolean_mock.return_value = True
        helm_manager = self.create_helm_manager(
            HelmConfig(
                charts=[
                    HelmChart(repo="stable", chart="chart-1"),
                    HelmChart(repo="stable", chart="chart-2"),
                ]
            ),
            installed_helm_charts=[
                HelmChartQualifiedName("default", "chart-2"),
                HelmChartQualifiedName("default", "chart-3"),
            ],
        )
        helm_manager.prune(additional_args=("--debug",))
        self.helm_run.assert_called_once_with("uninstall", "chart-3", "-n", "default", "--debug")

    @mock.patch("strong_opx.helm.input_boolean")
    def test_prune__reject_input(self, input_boolean_mock: mock.Mock):
        input_boolean_mock.return_value = False
        helm_manager = self.create_helm_manager(
            HelmConfig(
                charts=[
                    HelmChart(repo="stable", chart="chart-1"),
                    HelmChart(repo="stable", chart="chart-2"),
                ]
            ),
            installed_helm_charts=[
                HelmChartQualifiedName("default", "chart-2"),
                HelmChartQualifiedName("default", "chart-3"),
            ],
        )
        helm_manager.prune()
        self.helm_run.assert_not_called()
