from ipaddress import IPv4Address
from unittest import TestCase
from unittest.mock import Mock, patch

import pytest
from parameterized import parameterized

from strong_opx.project import Project
from strong_opx.providers import ComputeInstance, ComputeInstanceDescription
from strong_opx.providers.compute import ComputeInstanceState, filter_instances_by_environment_tag_if_exists
from strong_opx.utils.mapping import CaseInsensitiveMultiTagDict
from tests.mocks import create_mock_environment, create_mock_project

PUBLIC_IP = IPv4Address("1.2.3.4")
PRIVATE_IP = IPv4Address("10.2.3.4")


def create_mock_compute_instance_description(
    instance_id: str = None, tags: dict[str, str] = None
) -> ComputeInstanceDescription:
    if instance_id is None:
        instance_id = "mock-instance-id"

    return ComputeInstanceDescription(
        instance_id=instance_id,
        state=ComputeInstanceState.RUNNING,
        private_ip=PRIVATE_IP,
        public_ip=PUBLIC_IP,
        tags=CaseInsensitiveMultiTagDict(tags or {}),
    )


class ComputeInstanceTests(TestCase):
    @parameterized.expand(
        [
            "8.8.8.8",
            "192.168.1.1",
        ]
    )
    def test_ip(self, ip: str):
        instance = ComputeInstance.parse(ip)
        self.assertEqual(str(instance), ip)

    @patch("strong_opx.providers.compute.current_provider_class")
    def test_unsupported_instance_id(self, current_provider_class_mock):
        current_provider_class_mock.return_value.compute_instance_id_re = None

        with self.assertRaises(ValueError) as cm:
            ComputeInstance.parse("some-instance-id")

        self.assertEqual(str(cm.exception), "Expected 4 octets in 'some-instance-id'")

    @patch("strong_opx.providers.compute.current_provider_class")
    def test_invalid_instance_id(self, current_provider_class_mock):
        current_provider_class_mock.return_value.compute_instance_id_re = "[A-Z]+"

        with self.assertRaises(ValueError) as cm:
            ComputeInstance.parse("some-instance-id")

        self.assertEqual(str(cm.exception), "Invalid instance ID format: some-instance-id. Expected format: [A-Z]+")

    @patch("strong_opx.providers.compute.current_provider_class")
    def test_valid_instance_id(self, current_provider_class_mock):
        current_provider_class_mock.return_value.compute_instance_id_re = r"[A-Za-z0-9\-]+"

        instance = ComputeInstance.parse("some-instance-id")
        self.assertEqual(instance.instance_id, "some-instance-id")

    @parameterized.expand(
        [
            (
                "public_ip__no_instance",
                PUBLIC_IP,
                [],
                f'Unable to find an instance with public IP "{PUBLIC_IP}"',
            ),
            (
                "private_ip__no_instance",
                PRIVATE_IP,
                [],
                f'Unable to find an instance with private IP "{PRIVATE_IP}"',
            ),
            (
                "public_ip__multiple_instances",
                PUBLIC_IP,
                [
                    create_mock_compute_instance_description("instance1"),
                    create_mock_compute_instance_description("instance2"),
                ],
                (
                    'Expected to find exactly one instance with public IP "1.2.3.4", but '
                    "found 2. Instance IDs: instance1, instance2."
                ),
            ),
            (
                "public_ip__multiple_instances",
                PRIVATE_IP,
                [
                    create_mock_compute_instance_description("instance1"),
                    create_mock_compute_instance_description("instance2"),
                ],
                (
                    'Expected to find exactly one instance with private IP "10.2.3.4", but '
                    "found 2. Instance IDs: instance1, instance2."
                ),
            ),
        ],
    )
    @patch("strong_opx.providers.compute.current_provider", autospec=True)
    @patch("strong_opx.providers.compute.filter_instances_by_environment_tag_if_exists", autospec=True)
    def test_describe_should_raise_if_there_is_not_exactly_one_instance(
        self,
        name: str,
        ip_address: IPv4Address,
        instances: list[ComputeInstanceDescription],
        expected_error_message: str,
        filter_instances_by_environment_tag_if_exists_mock: Mock,
        current_provider_mock: Mock,
    ):
        filter_instances_by_environment_tag_if_exists_mock.side_effect = lambda x: x  # No filtering in this test

        current_provider_mock.return_value.query_compute_instances.return_value = instances
        instance = ComputeInstance(ip_address)

        with pytest.raises(ValueError) as e:
            instance.describe()

        current_provider_mock.return_value.query_compute_instances.assert_called_once_with(ip_address)
        assert str(e.value) == expected_error_message


class FilterByEnvironmentTagIfExistsTests(TestCase):
    @parameterized.expand(
        [
            ("no_instance__return_empty_array", [], []),
            (
                "Multiple environment tags, return so long as one value matches",
                [
                    create_mock_compute_instance_description(
                        instance_id="instance1", tags={"Environment": "not unittest", "ENVIRONMENT": "unittest"}
                    ),
                ],
                ["instance1"],
            ),
            (
                "One instance with matching environment & one with no environment, return both",
                [
                    create_mock_compute_instance_description(instance_id="instance1", tags={"EnViRoNmEnT": "unittest"}),
                    create_mock_compute_instance_description(
                        instance_id="instance2", tags={"EnViRoNmEnT": "something else"}
                    ),
                    create_mock_compute_instance_description(instance_id="instance3"),
                ],
                ["instance1", "instance3"],
            ),
        ]
    )
    @patch.object(Project, "current", autospec=True)
    def test_should_return_expected_value(
        self,
        name: str,
        instances: list[ComputeInstanceDescription],
        expected_instance_ids: list[str],
        current_project_mock: Mock,
    ):
        project_mock = create_mock_project()
        project_mock.selected_environment = create_mock_environment()

        current_project_mock.return_value = project_mock

        actual_instances = filter_instances_by_environment_tag_if_exists(instances)
        actual_instance_ids = [instance.instance_id for instance in actual_instances]

        assert actual_instance_ids == expected_instance_ids
