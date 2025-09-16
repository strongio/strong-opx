import json
import os.path
import tempfile
from functools import cached_property
from subprocess import CompletedProcess
from typing import TYPE_CHECKING, Optional, Union

from pydantic import AnyUrl, Field
from pydantic.dataclasses import dataclass

from strong_opx.exceptions import HelmError
from strong_opx.template import FileTemplate
from strong_opx.utils.prompt import input_boolean
from strong_opx.utils.shell import shell

if TYPE_CHECKING:
    from strong_opx.platforms import KubernetesPlatform

HELM_DEFAULT_REPO_NAME = "stable"
HELM_DEFAULT_REPO_URL = "https://charts.helm.sh/stable"


class HelmChartQualifiedName(str):
    def __new__(cls, namespace: str, name: str):
        instance = super().__new__(cls, f"{namespace}:{name}")
        instance.name = name
        instance.namespace = namespace
        return instance


@dataclass
class HelmChart:
    repo: str
    chart: str
    name: Optional[str] = None
    version: Optional[str] = None
    namespace: str = "default"
    environment: Optional[Union[list[str], str]] = None
    values: Optional[str] = None
    timeout: str = "5m0s"

    def __post_init__(self):
        if self.name is None:
            self.name = self.chart

    @cached_property
    def qualified_name(self) -> HelmChartQualifiedName:
        return HelmChartQualifiedName(self.namespace, self.name)


@dataclass
class HelmConfig:
    charts: list[HelmChart] = Field(default_factory=list)
    repos: dict[str, AnyUrl] = None

    def __post_init__(self):
        if self.repos is None:
            self.repos = {}
        else:
            self.repos = {k: str(v) for k, v in self.repos.items()}

        if HELM_DEFAULT_REPO_NAME not in self.repos:
            self.repos[HELM_DEFAULT_REPO_NAME] = HELM_DEFAULT_REPO_URL

        for repo, repo_url in self.repos.items():
            if not any(repo_url.startswith(prefix) for prefix in ("http://", "https://", "oci://")):
                raise HelmError(f"Invalid repo URL {repo_url} for {repo}. Must start with http://, https:// or oci://")


class HelmManager:
    def __init__(self, platform: "KubernetesPlatform"):
        self.platform = platform
        self.config_path = os.path.join(self.platform.project.path, "helm.yml")
        self.config = platform.project.helm_config or HelmConfig()

    @cached_property
    def installed_helm_charts(self) -> list[HelmChartQualifiedName]:
        output = json.loads(self.run("list", "--output", "json", "-A", capture_output=True).stdout.decode("utf8"))
        return [HelmChartQualifiedName(helm["namespace"], helm["name"]) for helm in output]

    def run(self, *additional_args: str, **kwargs) -> CompletedProcess:
        self.platform.configure_kubernetes()
        return shell(("helm", "--kubeconfig", self.platform.kube_config_path) + additional_args, **kwargs)

    def apply(self, upgrade: bool, charts: list[str] = None, additional_args: tuple[str, ...] = ()) -> None:
        if upgrade:
            cmd_prefix = ("upgrade", "--install")
        else:
            cmd_prefix = ("install",)

        for chart in self.config.charts:
            if not upgrade and chart.qualified_name in self.installed_helm_charts:
                continue

            if charts and chart.name not in charts:
                continue

            starting_args = [
                chart.name,
                chart.chart,
                "--repo",
                str(self.config.repos[chart.repo]),
            ]

            if str(self.config.repos[chart.repo]).startswith("oci://"):
                starting_args = [
                    chart.name,
                    str(self.config.repos[chart.repo]),
                ]

            args = [
                *starting_args,
                "-n",
                chart.namespace,
                "--create-namespace",
                "--wait",
                "--timeout",
                str(chart.timeout),
            ]

            if chart.version:
                args.append("--version")
                args.append(chart.version)

            if chart.values:
                file_path = os.path.join(self.platform.project.path, chart.values)
                if not os.path.exists(file_path):
                    raise HelmError(f"Unable to locate specified values {chart.values} for {chart.name}")

                with tempfile.NamedTemporaryFile(suffix=f"_{os.path.basename(file_path)}") as f:
                    FileTemplate(file_path).render_to_file(f.name, self.platform.environment.context)

                    args.append("--values")
                    args.append(f.name)
                    self.run(*cmd_prefix, *args, *additional_args)
            else:
                self.run(*cmd_prefix, *args, *additional_args)

    def prune(self, additional_args: list[str] = ()) -> bool:
        to_uninstall = [
            chart_name
            for chart_name in self.installed_helm_charts
            if all(chart.qualified_name != chart_name for chart in self.config.charts)
        ]

        if not to_uninstall:
            return False

        print("Following releases will be uninstalled")
        print("  {}".format("\n  ".join(to_uninstall)))

        if input_boolean("Do you want to continue", default=False):
            for helm in to_uninstall:
                self.run("uninstall", helm.name, "-n", helm.namespace, *additional_args)
