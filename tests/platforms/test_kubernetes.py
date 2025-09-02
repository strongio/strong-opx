from dataclasses import dataclass
from io import StringIO
from typing import Any, Optional
from unittest import mock

import pytest

from strong_opx.platforms.kubernetes import KubernetesPlatform
from strong_opx.providers.aws import AWSCredential
from tests.mocks import create_mock_environment, create_mock_project


@pytest.fixture
def mock_project() -> mock.Mock:
    return create_mock_project(config=mock.MagicMock(kubectl_executable="kubectl"))


@pytest.fixture()
def mock_environment(mock_project: mock.Mock) -> mock.Mock:
    return create_mock_environment(project=mock_project)


@pytest.fixture()
def kubernetes_platform(mock_project: mock.Mock, mock_environment: mock.Mock) -> KubernetesPlatform:
    return KubernetesPlatform(
        cluster_name="someCluster", service_role=None, project=mock_project, environment=mock_environment
    )


class TestKubernetesPlatform:
    @dataclass
    class Fixture:
        mock_provider: mock.Mock
        subject: KubernetesPlatform

    @dataclass
    class Params:
        description: str
        input_service_role: Optional[str]

    @pytest.fixture(
        ids=lambda x: x.description,
        params=[
            Params(description="no service role", input_service_role=None),
            Params(description="service role", input_service_role="someServiceRole"),
        ],
    )
    def setup(self, mock_project, mock_environment, request):
        mock_provider = mock.MagicMock()
        mock_project.provider = mock_provider

        return TestKubernetesPlatform.Fixture(
            subject=KubernetesPlatform(
                cluster_name="someCluster",
                service_role=request.param.input_service_role,
                project=mock_project,
                environment=mock_environment,
            ),
            mock_provider=mock_provider,
        )

    @pytest.mark.parametrize("config_exists", [True, False])
    @mock.patch.object(KubernetesPlatform, "_post_process_kubeconfig")
    @mock.patch("strong_opx.platforms.kubernetes.os", autospec=True)
    def test_configure_kubernetes(
        self,
        mock_os,
        mock_post_process_kubeconfig,
        config_exists,
        setup: Fixture,
    ):
        mock_os.path.exists.return_value = config_exists

        mock_assume_role = setup.mock_provider.assume_service_role
        mock_update_kubeconfig = setup.mock_provider.update_kubeconfig

        setup.subject.__dict__["kube_config_path"] = "someDirectory"
        setup.subject.configure_kubernetes()

        if setup.subject.service_role:
            mock_assume_role.assert_called_once_with(setup.subject.service_role)
        else:
            mock_assume_role.assert_not_called()

        if config_exists:
            mock_update_kubeconfig.assert_not_called()
            mock_post_process_kubeconfig.assert_not_called()
        else:
            mock_update_kubeconfig.assert_called_once_with(setup.subject.cluster_name, setup.subject.kube_config_path)
            mock_post_process_kubeconfig.assert_called_once()

    @pytest.mark.parametrize(
        "yaml_load,yaml_dump",
        [
            [
                {"users": [{"user": {"exec": {"env": [{"name": "SOME_ENV", "value": "someValue"}]}}}]},
                {"users": [{"user": {"exec": {}}}]},
            ],
            [
                {"users": [{"user": {"exec": {}}}]},
                {"users": [{"user": {"exec": {}}}]},
            ],
        ],
    )
    @mock.patch("strong_opx.platforms.kubernetes.KubernetesPlatform.kube_config_path", new_callable=mock.PropertyMock)
    @mock.patch("strong_opx.platforms.kubernetes.yaml", autospec=True)
    def test_post_process_kubeconfig(self, mock_yaml, mock_kube_config_path, yaml_load, yaml_dump, setup: Fixture):
        mock_kube_config_path.return_value = "somePath"
        mock_yaml.load.return_value = yaml_load
        setup.subject._post_process_kubeconfig()

        mock_yaml.load.assert_called_once_with("somePath")
        mock_yaml.dump.assert_called_once_with(yaml_dump, "somePath")

    @mock.patch("strong_opx.platforms.kubernetes.shell", autospec=True)
    @mock.patch("strong_opx.platforms.kubernetes.KubernetesPlatform.kube_config_path", new_callable=mock.PropertyMock)
    @mock.patch.object(KubernetesPlatform, "configure_kubernetes", autospec=True)
    def test_kubectl(self, mock_configure_kubernetes, mock_kube_config_path, mock_shell, setup: Fixture):
        mock_kube_config_path.return_value = "somePath"

        setup.subject.kubectl()

        mock_configure_kubernetes.assert_called_once()
        mock_shell.assert_called_once_with(("kubectl", "--kubeconfig", "somePath"))


@mock.patch("strong_opx.platforms.kubernetes.os")
def test_get_proxy_status__missing_status_file(os_mock: mock.Mock, kubernetes_platform: KubernetesPlatform):
    os_mock.path.exists.return_value = False
    assert kubernetes_platform.get_proxy_status() is None


@mock.patch("strong_opx.platforms.kubernetes.os")
@mock.patch("strong_opx.platforms.kubernetes.open")
def test_get_proxy_status__process_killed(
    open_mock: mock.Mock, os_mock: mock.Mock, kubernetes_platform: KubernetesPlatform
):
    def process_lookup_error(pid, signal):
        raise ProcessLookupError()

    open_mock.return_value.__enter__.return_value.readline.side_effect = ["1\n", "8000\n"]
    os_mock.path.exists.return_value = True
    os_mock.kill.side_effect = process_lookup_error

    assert kubernetes_platform.get_proxy_status() is None


@mock.patch("strong_opx.platforms.kubernetes.os")
@mock.patch("strong_opx.platforms.kubernetes.open")
def test_get_proxy_status__all_good(open_mock: mock.Mock, os_mock: mock.Mock, kubernetes_platform: KubernetesPlatform):
    def process_lookup_error(pid, signal):
        assert pid == 1
        assert signal == 0

    open_mock.return_value.__enter__.return_value.readline.side_effect = ["1\n", "8000\n"]
    os_mock.path.exists.return_value = True
    os_mock.kill.side_effect = process_lookup_error

    assert kubernetes_platform.get_proxy_status() == (1, 8000)


@mock.patch("strong_opx.platforms.kubernetes.os")
@mock.patch("strong_opx.platforms.kubernetes.open")
def test_get_proxy_status__missing_pid(
    open_mock: mock.Mock, os_mock: mock.Mock, kubernetes_platform: KubernetesPlatform
):
    open_mock.return_value.__enter__.return_value.readline.side_effect = ["\n", "8000\n"]
    os_mock.path.exists.return_value = True

    os_mock.kill.assert_not_called()
    assert kubernetes_platform.get_proxy_status() == (None, 8000)


@mock.patch("strong_opx.platforms.kubernetes.open")
def test_save_proxy_status(open_mock: mock.Mock, kubernetes_platform: KubernetesPlatform):
    stream = StringIO()
    open_mock.return_value.__enter__.return_value = stream

    kubernetes_platform.save_proxy_status(1, 8000)
    assert stream.getvalue() == "1\n8000"


@pytest.mark.parametrize("pid", (None, 0, 100))
@mock.patch("strong_opx.platforms.kubernetes.os")
@mock.patch.object(KubernetesPlatform, "get_proxy_status", autospec=True)
def test_stop_proxy(
    get_proxy_status_mock: mock.Mock, os_mock: mock.Mock, pid: int, kubernetes_platform: KubernetesPlatform
):
    get_proxy_status_mock.return_value = (pid, 9000)
    kubernetes_platform.stop_proxy()

    if pid is None:
        os_mock.killpg.assert_not_called()
    else:
        os_mock.killpg.assert_called_once()


@mock.patch.object(KubernetesPlatform, "get_proxy_status", autospec=True)
def test_stop_proxy__no_status(get_proxy_status_mock: mock.Mock, kubernetes_platform: KubernetesPlatform):
    get_proxy_status_mock.return_value = None
    assert not kubernetes_platform.stop_proxy()


class TestStartProxy:
    @dataclass
    class Param:
        detached: bool
        proxy_status: Optional[tuple[int, int]]
        description: str

    @dataclass
    class Fixture:
        popen_mock: mock.Mock
        proxy_lock_mock: mock.Mock
        configure_kubernetes_mock: mock.Mock
        get_free_tcp_port_mock: mock.Mock
        save_proxy_status_mock: mock.Mock
        params: Any

    @pytest.fixture(
        ids=lambda x: x.description,
        params=[
            Param(detached=False, proxy_status=(100, 9000), description="already running"),
            Param(detached=False, proxy_status=None, description="not running"),
            Param(detached=True, proxy_status=None, description="run in detached mode"),
        ],
    )
    @mock.patch("strong_opx.platforms.kubernetes.Popen", autospec=True)
    @mock.patch("strong_opx.platforms.kubernetes.get_free_tcp_port", return_value=9000)
    @mock.patch.object(KubernetesPlatform, "get_proxy_status")
    @mock.patch.object(KubernetesPlatform, "save_proxy_status")
    @mock.patch.object(KubernetesPlatform, "proxy_lock")
    @mock.patch.object(KubernetesPlatform, "configure_kubernetes")
    def setup(
        self,
        configure_kubernetes_mock: mock.Mock,
        proxy_lock_mock: mock.Mock,
        save_proxy_status_mock: mock.Mock,
        get_proxy_status_mock: mock.Mock,
        get_free_tcp_port_mock: mock.Mock,
        popen_mock: mock.Mock,
        kubernetes_platform: KubernetesPlatform,
        request,
    ) -> Fixture:
        params: TestStartProxy.Param = request.param

        get_proxy_status_mock.return_value = params.proxy_status
        popen_mock.return_value = mock.MagicMock(pid=100)

        kubernetes_platform.start_proxy(params.detached)
        return TestStartProxy.Fixture(
            popen_mock=popen_mock,
            proxy_lock_mock=proxy_lock_mock,
            get_free_tcp_port_mock=get_free_tcp_port_mock,
            configure_kubernetes_mock=configure_kubernetes_mock,
            save_proxy_status_mock=save_proxy_status_mock,
            params=params,
        )

    def test_lock_acquired(self, setup: Fixture):
        setup.proxy_lock_mock.assert_called_once()

    def test_get_free_tcp_port_not_called_if_already_running(self, setup: Fixture):
        if setup.params.proxy_status is None:
            setup.get_free_tcp_port_mock.assert_called_once()
        else:
            setup.get_free_tcp_port_mock.assert_not_called()

    def test_k8s_is_configured(self, setup: Fixture):
        if setup.params.proxy_status is None:
            setup.configure_kubernetes_mock.assert_called_once()
        else:
            setup.configure_kubernetes_mock.assert_not_called()

    def test_kubectl_proxy(self, setup: Fixture, kubernetes_platform: KubernetesPlatform):
        if setup.params.proxy_status is None:
            setup.popen_mock.assert_called_once_with(
                ("kubectl", "--kubeconfig", kubernetes_platform.kube_config_path, "proxy", "-p", "9000"),
                start_new_session=True,
            )
        else:
            setup.popen_mock.assert_not_called()

    def test_run_in_attached_mode(self, setup: Fixture):
        if setup.params.proxy_status is None and not setup.params.detached:
            setup.popen_mock.return_value.wait.assert_called_once()
        else:
            setup.popen_mock.return_value.wait.assert_not_called()

    def test_status_saved(self, setup: Fixture):
        if setup.params.proxy_status is None:
            setup.save_proxy_status_mock.assert_called_once_with(100, 9000)
        else:
            setup.save_proxy_status_mock.assert_not_called()
