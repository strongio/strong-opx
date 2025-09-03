from unittest import TestCase

from parameterized import parameterized

from strong_opx.project.vars import VariableConfig
from tests.mocks import create_mock_environment, create_mock_project


class VariableConfigTest(TestCase):
    def setUp(self) -> None:
        self.project = create_mock_project()
        self.environment = create_mock_environment(name="unittest", project=self.project)

    @parameterized.expand(
        [
            ("{{ ENVIRONMENT }}.yml", ["unittest.yml"]),
            (["{{ ENVIRONMENT }}/something.yml", "{{ ENVIRONMENT }}.yml"], ["unittest/something.yml", "unittest.yml"]),
            ({"unittest": "something.yml"}, ["something.yml"]),
            ({"some-env": "something.yml"}, []),
            ({"unittest": ["var1.yml", "var2.yml"]}, ["var1.yml", "var2.yml"]),
            ({"some-env": ["var1.yml", "var2.yml"]}, []),
            (["{{ ENVIRONMENT }}/something.yml", {"unittest": "var1.yml"}], ["unittest/something.yml", "var1.yml"]),
            (["common.yml", {"unittest": ["var1.yml", "var2.yml"]}], ["common.yml", "var1.yml", "var2.yml"]),
            (["common.yml", {"some-env": ["var1.yml", "var2.yml"]}], ["common.yml"]),
        ]
    )
    def test_get_paths(self, value, expected_paths):
        paths = VariableConfig(value=value).get_paths(self.environment)
        self.assertListEqual(paths, expected_paths)
