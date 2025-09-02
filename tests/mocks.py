import os
from typing import Optional, TypeVar, Union
from unittest import mock

from pydantic import TypeAdapter

from strong_opx.platforms import KubernetesPlatform, Platform
from strong_opx.project import Environment, Project
from strong_opx.providers import discovery
from strong_opx.template import Context

T = TypeVar("T")


def create_mock_project(**kwargs) -> Union[mock.Mock, Project]:
    name = kwargs.pop("name", "unittest")
    provider_name: Optional[str] = kwargs.pop("provider", None)
    provider_config = kwargs.pop("provider_config", {})

    project = mock.MagicMock(spec=Project, path="/tmp/unittest", **kwargs)
    project.name = name
    project.environments_dir = os.path.join(project.path, "environments")

    if provider_name is not None:
        discovery._selected_provider_name = provider_name
        provider_cls = discovery.get_provider_class(provider_name)
        project.provider = TypeAdapter(provider_cls).validate_python(provider_config)

    return project


def create_mock_environment(**kwargs) -> Union[mock.Mock, Environment]:
    name = kwargs.pop("name", "unittest")
    kwargs.setdefault("platforms", [])
    kwargs.setdefault("path", os.path.join("/tmp/unittest", name))
    kwargs.setdefault("base_context", Context({"ENVIRONMENT": name}))
    environment = mock.MagicMock(spec=Environment, **kwargs)
    environment.name = name
    return environment


def create_mock_platform(cls: type[T] = Platform, **kwargs) -> T:
    return mock.MagicMock(spec=cls, **kwargs)


def create_mock_kubernetes_platform(**kwargs) -> Union[mock.Mock, KubernetesPlatform]:
    return create_mock_platform(cls=KubernetesPlatform, **kwargs)
