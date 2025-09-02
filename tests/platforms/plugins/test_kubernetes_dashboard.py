from dataclasses import dataclass
from subprocess import CompletedProcess
from unittest import mock

import pytest

from strong_opx.exceptions import ProcessError
from strong_opx.platforms.plugins import KubernetesDashboardPlugin


@mock.patch("strong_opx.platforms.plugins.kubernetes_dashboard.tempfile")
def test_install(tempfile_mock: mock.Mock):
    tempfile_mock.NamedTemporaryFile.return_value.__enter__.return_value.name = "some-file.yml"

    platform = mock.MagicMock()
    plugin = KubernetesDashboardPlugin(platform=platform)
    plugin.config_url = "some-config.yml"
    plugin.install()
    platform.kubectl.assert_has_calls(
        [mock.call("apply", "-f", "some-config.yml"), mock.call("apply", "-f", "some-file.yml")]
    )


def test_is_installed():
    platform = mock.MagicMock()
    platform.kubectl.return_value = mock.MagicMock(spec=CompletedProcess, returncode=0)

    plugin = KubernetesDashboardPlugin(platform=platform)
    assert plugin.is_installed()


def test_is_installed__no_install():
    platform = mock.MagicMock()
    platform.kubectl.return_value = mock.MagicMock(
        spec=CompletedProcess,
        returncode=1,
        stderr=b"Unable to locate service (NotFound) kubernetes-dashboard",
    )

    plugin = KubernetesDashboardPlugin(platform=platform)
    assert not plugin.is_installed()


def test_is_installed__process_error_during_check():
    platform = mock.MagicMock()
    platform.kubectl.return_value = mock.MagicMock(
        spec=CompletedProcess,
        returncode=1,
        stderr=b"helm error",
    )

    plugin = KubernetesDashboardPlugin(platform=platform)
    with pytest.raises(ProcessError):
        plugin.is_installed()


class TestDashboardUp:
    @dataclass
    class Param:
        open_browser: bool
        detached: bool
        description: str

    @pytest.fixture(
        ids=lambda x: x.description,
        params=[
            Param(open_browser=False, detached=False, description="no browser"),
            Param(open_browser=True, detached=False, description="open browser in detached mode"),
            Param(open_browser=True, detached=False, description="open browser in attached mode"),
        ],
    )
    @mock.patch("strong_opx.platforms.plugins.kubernetes_dashboard.webbrowser")
    @mock.patch("strong_opx.platforms.plugins.kubernetes_dashboard.time")
    def operation(
        self,
        time_mock: mock.Mock,
        webbrowser_mock: mock.Mock,
        request,
    ):
        params: TestDashboardUp.Param = request.param

        platform = mock.MagicMock()
        platform.kube_config_path = "kubeconfig"
        platform.get_proxy_status.return_value = [0, 9000]
        plugin = KubernetesDashboardPlugin(platform=platform)

        plugin.up(open_browser=params.open_browser, detached=params.detached)
        return {
            "params": params,
            "plugin": plugin,
            "webbrowser_mock": webbrowser_mock,
        }

    def test_browser_opened(self, operation):
        params: TestDashboardUp.Param = operation["params"]

        if params.open_browser:
            operation["webbrowser_mock"].open.assert_called_once()
        else:
            operation["webbrowser_mock"].open.assert_not_called()

    def test_start_proxy_is_called(self, operation):
        operation["plugin"].platform.start_proxy.assert_called_once()


def test_get_secret_name():
    platform = mock.MagicMock()
    platform.kube_config_path = "kubeconfig"
    platform.kubectl.return_value = mock.Mock(
        spec=CompletedProcess, stdout=b"secret-abc\nsome-other-name\neks-admin-secret-124"
    )

    plugin = KubernetesDashboardPlugin(platform=platform)

    assert plugin.get_secret_name() == "eks-admin-secret-124"
