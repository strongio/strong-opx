from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import Mock

import pytest
from pydantic import BaseModel, ValidationError

from strong_opx.platforms import Platform
from strong_opx.project import Environment, Project


class PlatformConfig(BaseModel):
    required_field: str
    optional_field: Optional[str] = None


class NamespacedPlatform(Platform):
    config_class = PlatformConfig
    config_namespace = "namespace"


class GeneralPlatform(Platform):
    config_class = PlatformConfig


class TestPlatformFromConfig:
    @dataclass
    class Parameters:
        description: str
        config: dict[str, Any]
        platform_class: type[Platform]
        expected_config: Optional[dict[str, Any]]

    @dataclass
    class Fixture:
        platform: Optional[NamespacedPlatform]
        expected_config: Optional[dict[str, Any]]

    @pytest.fixture(
        ids=lambda x: x.description,
        params=[
            Parameters(
                description="no config",
                config={},
                expected_config=None,
                platform_class=GeneralPlatform,
            ),
            Parameters(
                description="no relevant config",
                config={"some_value": 12},
                expected_config=None,
                platform_class=GeneralPlatform,
            ),
            Parameters(
                description="only required config",
                config={"required_field": "value"},
                expected_config={"required_field": "value", "optional_field": None},
                platform_class=GeneralPlatform,
            ),
            Parameters(
                description="required and optional config",
                config={"required_field": "value", "optional_field": "value"},
                expected_config={"required_field": "value", "optional_field": "value"},
                platform_class=GeneralPlatform,
            ),
            Parameters(
                description="namespaced config",
                config={"namespace": {"required_field": "value", "optional_field": "value"}},
                expected_config={"required_field": "value", "optional_field": "value"},
                platform_class=NamespacedPlatform,
            ),
        ],
    )
    def setup(self, request) -> Fixture:
        project = Mock(spec=Project)
        environment = Mock(spec=Environment)
        params: TestPlatformFromConfig.Parameters = request.param

        platform = params.platform_class.from_config(project=project, environment=environment, **params.config)
        return TestPlatformFromConfig.Fixture(
            platform=platform,
            expected_config=params.expected_config,
        )

    def test_platform_init(self, setup: Fixture):
        if setup.expected_config is not None:
            assert setup.platform is not None
        else:
            assert setup.platform is None

    def test_platform_config_lading(self, setup: Fixture):
        if setup.expected_config is not None:
            for k, expected_value in setup.expected_config.items():
                current_value = getattr(setup.platform, k, None)
                assert current_value == expected_value


def test_invalid_namespace_platform_config():
    project = Mock(spec=Project)
    environment = Mock(spec=Environment)

    with pytest.raises(ValidationError):
        NamespacedPlatform.from_config(project=project, environment=environment, namespace={"key": "value"})
