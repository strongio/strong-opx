from dataclasses import dataclass
from typing import Union
from unittest import TestCase, mock

import pytest

from strong_opx.exceptions import ProjectEnvironmentError
from strong_opx.platforms import GenericPlatform, Platform
from strong_opx.project.base import Project
from strong_opx.project.environment import Environment, load_environment
from tests.mocks import create_mock_environment, create_mock_platform, create_mock_project


class EnvironmentTests(TestCase):
    def setUp(self) -> None:
        self.project = create_mock_project()
        self.environment = create_mock_environment(name="unittest", project=self.project)

    def test_select_platform(self):
        self.environment.platforms = [create_mock_platform(cls=GenericPlatform)]

        platform = Environment.select_platform(self.environment, GenericPlatform)
        self.assertIsInstance(platform, GenericPlatform)

    def test_select_platform__unknown_platform(self):
        with self.assertRaises(ProjectEnvironmentError) as ex:
            Environment.select_platform(self.environment, GenericPlatform)

        self.assertEqual(str(ex.exception), "Environment unittest does not support GenericPlatform")

    def test_register_platform(self):
        platform = create_mock_platform()
        Environment.register_platform(self.environment, platform)
        self.assertEqual(self.environment.platforms, [platform])
        platform.init_context.assert_called_once()


class TestLoadEnvironment:
    @dataclass
    class Parameters:
        description: str
        platform_1_from_config: Union[None, mock.Mock]
        platform_2_from_config: Union[None, mock.Mock]
        expected_platforms: list[mock.Mock]

    @dataclass
    class Fixture:
        environment: Environment
        mock_environment: mock.Mock
        mock_environment_constructor: mock.Mock
        mock_project: mock.Mock
        mock_yaml: mock.Mock
        mock_os: mock.Mock
        config: dict
        expected_platforms: list[mock.Mock]

    mock_platform_1 = mock.Mock(spec=Platform)
    mock_platform_2 = mock.Mock(spec=Platform)
    mock_all_platforms = [mock_platform_1, mock_platform_2]

    @pytest.fixture(
        ids=lambda x: x.description,
        params=[
            Parameters(
                description="no platform",
                expected_platforms=[],
                platform_1_from_config=None,
                platform_2_from_config=None,
            ),
            Parameters(
                description="1 platform",
                platform_1_from_config=None,
                platform_2_from_config=mock.Mock(spec=Platform),
                expected_platforms=[mock_platform_2],
            ),
            Parameters(
                description="all platforms",
                platform_1_from_config=mock.Mock(spec=Platform),
                platform_2_from_config=mock.Mock(spec=Platform),
                expected_platforms=[mock_platform_1, mock_platform_2],
            ),
        ],
    )
    @mock.patch("strong_opx.project.environment.ALL_PLATFORMS", mock_all_platforms)
    @mock.patch("strong_opx.project.environment.os", autospec=True)
    @mock.patch("strong_opx.project.environment.yaml", autospec=True)
    @mock.patch("strong_opx.project.environment.Environment", autospec=True)
    def setup(
        self, mock_environment_constructor: mock.Mock, yaml_mock: mock.Mock, os_mock: mock.Mock, request
    ) -> Fixture:
        TestLoadEnvironment.mock_platform_1.reset_mock()
        TestLoadEnvironment.mock_platform_2.reset_mock()

        params: TestLoadEnvironment.Parameters = request.param

        TestLoadEnvironment.mock_platform_1.from_config.return_value = params.platform_1_from_config
        TestLoadEnvironment.mock_platform_2.from_config.return_value = params.platform_2_from_config

        os_mock.path.exists.return_value = True
        os_mock.path.isfile.return_value = True
        mock_config = {"some": "config"}
        yaml_mock.load.return_value = mock_config

        mock_project = create_mock_project(provider="aws")

        mock_environment = create_mock_environment(project=mock_project)
        mock_environment.register_platform = lambda x: Environment.register_platform(mock_environment, x)
        mock_environment_constructor.return_value = mock_environment

        environment = load_environment("example", mock_project)

        return TestLoadEnvironment.Fixture(
            environment=environment,
            expected_platforms=params.expected_platforms,
            mock_environment=mock_environment,
            mock_environment_constructor=mock_environment_constructor,
            mock_project=mock_project,
            mock_yaml=yaml_mock,
            mock_os=os_mock,
            config=mock_config,
        )

    def test_os_path_join(self, setup: Fixture):
        setup.mock_os.path.join.assert_called_once_with(setup.mock_project.environments_dir, "example", "config.yml")

    def test_load_yaml(self, setup: Fixture):
        setup.mock_yaml.load.assert_called_once_with(setup.mock_os.path.join.return_value)

    def test_should_call_environment(self, setup: Fixture):
        setup.mock_environment_constructor.assert_called_once_with(name="example", project=setup.mock_project, vars_={})

    def test_from_config(self, setup: Fixture):
        TestLoadEnvironment.mock_platform_1.from_config.assert_called_once_with(
            project=setup.mock_project, environment=setup.mock_environment, **setup.config
        )
        TestLoadEnvironment.mock_platform_2.from_config.assert_called_once_with(
            project=setup.mock_project, environment=setup.mock_environment, **setup.config
        )

    def test_should_contain_correct_platforms(self, setup: Fixture):
        expected_platforms = list(map(lambda x: x.from_config.return_value, setup.expected_platforms))
        assert setup.environment.platforms == expected_platforms


@mock.patch("strong_opx.project.environment.os", autospec=True)
def test_missing_config_file(os_mock: mock.Mock):
    os_mock.path.exists.return_value = False
    os_mock.path.isfile.return_value = False

    project = mock.Mock(spec=Project)
    project.environments_dir = "somewhere"

    with pytest.raises(ProjectEnvironmentError):
        load_environment("unknown", project)

    os_mock.path.exists.assert_called_once()
