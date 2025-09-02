import argparse
import base64
import json
import tempfile
import threading
import time
import webbrowser
from typing import TYPE_CHECKING

from strong_opx.exceptions import PluginError, ProcessError
from strong_opx.platforms.plugins.plugin import PlatformPlugin

if TYPE_CHECKING:
    from strong_opx.platforms.kubernetes import KubernetesPlatform

EKS_ADMIN_NAME = "eks-admin"
EKS_ADMIN_SERVICE_ACCOUNT = f"""
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {EKS_ADMIN_NAME}
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: {EKS_ADMIN_NAME}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: {EKS_ADMIN_NAME}
  namespace: kube-system
  """


class KubernetesDashboardPlugin(PlatformPlugin):
    platform: "KubernetesPlatform"
    config_url = "https://raw.githubusercontent.com/kubernetes/dashboard/v2.0.5/aio/deploy/recommended.yaml"

    def is_installed(self) -> bool:
        output = self.platform.kubectl(
            "get",
            "service",
            "kubernetes-dashboard",
            "-n",
            "kubernetes-dashboard",
            capture_output=True,
            ignore_exit_code=True,
        )
        if output.returncode:
            if b"(NotFound)" in output.stderr:
                return False

            raise ProcessError(output.stderr)

        return True

    def install(self) -> None:
        self.platform.kubectl("apply", "-f", self.config_url)

        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+") as f:
            f.write(EKS_ADMIN_SERVICE_ACCOUNT)
            f.flush()

            self.platform.kubectl("apply", "-f", f.name)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(title="operation", description="Operation to execute", required=True)

        up_parser = subparsers.add_parser("up", help="Start Kubernetes Dashboard")
        up_parser.add_argument("-d", "--detach", action="store_true", dest="detached", default=False)
        up_parser.add_argument("--no-browser", action="store_false", dest="open_browser", default=True)
        up_parser.set_defaults(operation="up")

        down_parser = subparsers.add_parser("down", help="Stop Kubernetes Dashboard")
        down_parser.set_defaults(operation="down")

        token_parser = subparsers.add_parser("token", help="Get Kubernetes Dashboard auth token")
        token_parser.set_defaults(operation="token")

    def up(self, open_browser: bool, detached: bool):
        def delayed_open_browser():
            port = None
            time.sleep(1)
            while True:
                status = self.platform.get_proxy_status()
                if status is None:
                    time.sleep(1)
                    continue

                _, port = status
                break

            time.sleep(1)
            webbrowser.open(
                f"http://localhost:{port}/api/v1/namespaces/kubernetes-dashboard/services"
                f"/https:kubernetes-dashboard:/proxy/#!/login",
                new=2,
            )

        open_browser_thread = None
        if open_browser:
            open_browser_thread = threading.Thread(target=delayed_open_browser)
            open_browser_thread.start()

        self.platform.start_proxy(detached)
        if open_browser_thread is not None:
            open_browser_thread.join()

    def get_secret_name(self) -> str:
        output = self.platform.kubectl("-n=kube-system", "get", "secret", "-o=name", capture_output=True).stdout
        matching_lines = [line for line in output.decode("utf8").split() if EKS_ADMIN_NAME in line]
        if not matching_lines:
            raise PluginError(f"Unable to locate secret for {EKS_ADMIN_NAME}")

        return matching_lines[0]

    def token(self):
        self.platform.ensure_proxy_is_running()
        secret_name = self.get_secret_name()

        output = self.platform.kubectl("-n=kube-system", "get", "-o=json", secret_name, capture_output=True)

        secret_detail = json.loads(output.stdout.decode("utf8"))
        secret_token = secret_detail["data"]["token"]
        secret_token = base64.b64decode(secret_token).decode("utf8")

        print("\nUse the following token to log into the Kubernetes Dashboard:\n")
        print(secret_token)
        print()

    def handle(self, operation: str, **kwargs):
        if operation == "up":
            self.up(**kwargs)
        elif operation == "down":
            self.platform.stop_proxy()
        elif operation == "token":
            self.token()
