from copy import deepcopy
from dataclasses import dataclass, field
from typing import Iterable
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch

import pytest

from strong_opx.management.commands import compute  # import the module, so we can monkeypatch global-scope items
from strong_opx.platforms import GenericPlatform
from strong_opx.providers import ComputeInstance
from strong_opx.providers.compute import ComputeInstanceState
from tests.helper_functions import assert_has_calls_exactly
from tests.mocks import create_mock_environment, create_mock_platform, create_mock_project

_DO_NOT_CARE_ARBITRARY_BOOL = True


class TestCommand:
    class TestSortByState:
        @dataclass
        class Fixture:
            hosts: list[ComputeInstance]
            actual_instance_states: dict
            actual_running_instances: list[str]
            actual_stopped_instances: list[str]

        @pytest.fixture
        @patch.object(ComputeInstance, "current_state", new_callable=PropertyMock)
        def setup(self, current_state_mock: Mock) -> Fixture:
            current_state_mock.side_effect = [
                ComputeInstanceState.STOPPED,
                ComputeInstanceState.RUNNING,
                ComputeInstanceState.RUNNING,
                ComputeInstanceState.UNKNOWN,
            ]
            hosts = [ComputeInstance.parse(ip) for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4")]

            for host_id, host in enumerate(hosts, 1):
                host._instance_id = str(host_id)

            # noinspection PyProtectedMember
            actual_instance_states, actual_running_instances, actual_stopped_instances = compute.Command._sort_by_state(
                hosts
            )

            return self.Fixture(
                hosts=hosts,
                actual_instance_states=actual_instance_states,
                actual_running_instances=actual_running_instances,
                actual_stopped_instances=actual_stopped_instances,
            )

        def test_should_return_the_expected_instance_states(self, setup: Fixture):
            expected_instance_states = {
                setup.hosts[0]: ComputeInstanceState.STOPPED,
                setup.hosts[1]: ComputeInstanceState.RUNNING,
                setup.hosts[2]: ComputeInstanceState.RUNNING,
                setup.hosts[3]: ComputeInstanceState.UNKNOWN,
            }

            assert setup.actual_instance_states == expected_instance_states

        def test_should_return_the_expected_running_instances(self, setup: Fixture):
            expected_running_instances = ["2", "3"]
            assert setup.actual_running_instances == expected_running_instances

        def test_should_return_the_expected_stopped_instances(self, setup: Fixture):
            expected_stopped_instances = ["1"]
            assert setup.actual_stopped_instances == expected_stopped_instances

    class TestRaiseForAnyInvalidStates:
        def test_should_raise_if_any_states_are_invalid(self):
            instance_states = {
                ComputeInstance.parse("1.1.1.1"): ComputeInstanceState.RUNNING,
                ComputeInstance.parse("9.0.0.0"): ComputeInstanceState.UNKNOWN,
                ComputeInstance.parse("8.0.0.0"): ComputeInstanceState.UNKNOWN,
            }

            with pytest.raises(RuntimeError) as exception_info:
                compute.Command._raise_for_any_invalid_states(instance_states)

            actual_message = str(exception_info.value)
            expected_message = (
                "Found 2 instance(s) with an invalid state: (IP=9.0.0.0, State=unknown), " "(IP=8.0.0.0, State=unknown)"
            )

            assert actual_message == expected_message

    class TestHandle:
        instance_states = {
            ComputeInstance.parse("1.1.1.1"): ComputeInstanceState.RUNNING,
            ComputeInstance.parse("2.2.2.2"): ComputeInstanceState.RUNNING,
            ComputeInstance.parse("9.9.9.9"): ComputeInstanceState.STOPPED,
        }
        running_instances = ["1", "2"]
        stopped_instances = ["9"]

        @staticmethod
        def _resolve_instance(host_or_ip: str):
            ret_map = {
                "red": [ComputeInstance.parse("1.1.1.1"), ComputeInstance.parse("2.2.2.2")],
                "blue": [ComputeInstance.parse("9.9.9.9")],
            }

            return ret_map[host_or_ip]

        platform_mock: MagicMock = create_mock_platform(GenericPlatform)
        project_mock = create_mock_project()

        @dataclass
        class Parameters:
            description: str
            operation: str
            wait: bool

            expected_log_instance_states_calls: list["call"] = field(default_factory=list)
            expected_raise_for_any_invalid_states: list["call"] = field(default_factory=list)

            expected_start_or_stop_instances_calls: list["call"] = field(default_factory=list)

        @dataclass
        class Fixture:
            environment_mock: MagicMock

            expected_log_instance_states_calls: Iterable["call"]
            expected_raise_for_any_invalid_states: Iterable["call"]

            expected_start_or_stop_instances_calls: list["call"]

            sort_by_state_mock: MagicMock
            log_states_of_ips_mock: MagicMock
            platform_mock: MagicMock
            raise_for_any_invalid_states_mock: MagicMock
            start_or_stop_instances_mock: MagicMock
            subject: compute.Command

        @pytest.fixture(
            ids=lambda x: x.description,
            params=[
                Parameters(
                    description='"status" operation',
                    operation="status",
                    wait=_DO_NOT_CARE_ARBITRARY_BOOL,
                    expected_log_instance_states_calls=[
                        call(
                            deepcopy(instance_states),
                            [
                                ComputeInstance.parse("1.1.1.1"),
                                ComputeInstance.parse("2.2.2.2"),
                                ComputeInstance.parse("9.9.9.9"),
                            ],
                        )
                    ],
                ),
                Parameters(
                    description='"stop" operation, no waiting',
                    operation="stop",
                    wait=False,
                    expected_raise_for_any_invalid_states=[call(deepcopy(instance_states))],
                    expected_start_or_stop_instances_calls=[
                        call(project=project_mock, instance_ids=["1", "2"], operation="stop", wait=False)
                    ],
                ),
                Parameters(
                    description='"stop" operation, with waiting',
                    operation="stop",
                    wait=True,
                    expected_raise_for_any_invalid_states=[call(deepcopy(instance_states))],
                    expected_start_or_stop_instances_calls=[
                        call(project=project_mock, instance_ids=["1", "2"], operation="stop", wait=True)
                    ],
                ),
                Parameters(
                    description='"start" operation, no waiting',
                    operation="start",
                    wait=False,
                    expected_raise_for_any_invalid_states=[call(deepcopy(instance_states))],
                    expected_start_or_stop_instances_calls=[
                        call(project=project_mock, instance_ids=["9"], operation="start", wait=False)
                    ],
                ),
                Parameters(
                    description='"start" operation, with waiting',
                    operation="start",
                    wait=True,
                    expected_raise_for_any_invalid_states=[call(deepcopy(instance_states))],
                    expected_start_or_stop_instances_calls=[
                        call(project=project_mock, instance_ids=["9"], operation="start", wait=True)
                    ],
                ),
                Parameters(
                    description='"restart" operation, no waiting',
                    operation="restart",
                    wait=False,
                    expected_raise_for_any_invalid_states=[call(deepcopy(instance_states))],
                    expected_start_or_stop_instances_calls=[
                        call(project=project_mock, instance_ids=["1", "2"], operation="stop", wait=True),
                        call(project=project_mock, instance_ids=["9", "1", "2"], operation="start", wait=False),
                    ],
                ),
                Parameters(
                    description='"restart" operation, with waiting',
                    operation="restart",
                    wait=True,
                    expected_raise_for_any_invalid_states=[call(deepcopy(instance_states))],
                    expected_start_or_stop_instances_calls=[
                        call(project=project_mock, instance_ids=["1", "2"], operation="stop", wait=True),
                        call(project=project_mock, instance_ids=["9", "1", "2"], operation="start", wait=True),
                    ],
                ),
            ],
        )
        @patch.object(compute.Command, "_start_or_stop_instances", autospec=True)
        @patch.object(compute.Command, "_raise_for_any_invalid_states", autospec=True)
        @patch.object(compute.Command, "_log_instance_states", autospec=True)
        @patch.object(compute.Command, "_sort_by_state", autospec=True)
        def setup(
            self,
            sort_by_state_mock: MagicMock,
            log_states_of_ips_mock: MagicMock,
            raise_for_any_invalid_states_mock: MagicMock,
            start_or_stop_instances_mock: MagicMock,
            request,
        ):
            params: TestCommand.TestHandle.Parameters = request.param

            self.project_mock.reset_mock()
            self.platform_mock.reset_mock()
            self.platform_mock.resolve_instance.side_effect = self._resolve_instance

            environment_mock = create_mock_environment()
            environment_mock.select_platform.return_value = self.platform_mock

            # Using deepcopy() to avoid altering the original values
            sort_by_state_mock.return_value = (
                deepcopy(self.instance_states),
                deepcopy(self.running_instances),
                deepcopy(self.stopped_instances),
            )

            subject = compute.Command()
            subject.handle(
                environment=environment_mock,
                project=self.project_mock,
                operation=params.operation,
                host_or_group=["red", "blue"],
                wait=params.wait,
            )

            # noinspection PyTypeChecker
            return self.Fixture(
                environment_mock=environment_mock,
                expected_log_instance_states_calls=params.expected_log_instance_states_calls,
                expected_raise_for_any_invalid_states=params.expected_raise_for_any_invalid_states,
                expected_start_or_stop_instances_calls=params.expected_start_or_stop_instances_calls,
                sort_by_state_mock=sort_by_state_mock,
                log_states_of_ips_mock=log_states_of_ips_mock,
                platform_mock=self.platform_mock,
                raise_for_any_invalid_states_mock=raise_for_any_invalid_states_mock,
                start_or_stop_instances_mock=start_or_stop_instances_mock,
                subject=subject,
            )

        def test_should_call_select_platform(self, setup: Fixture):
            setup.environment_mock.select_platform.assert_called_once_with(GenericPlatform)

        def test_should_call_sort_by_state(self, setup: Fixture):
            setup.sort_by_state_mock.assert_called_once_with(
                [ComputeInstance.parse("1.1.1.1"), ComputeInstance.parse("2.2.2.2"), ComputeInstance.parse("9.9.9.9")]
            )

        def test_should_have_expected_calls_for_log_instance_states(self, setup: Fixture):
            assert_has_calls_exactly(
                mock=setup.log_states_of_ips_mock, expected_calls=setup.expected_log_instance_states_calls
            )

        def test_should_have_expected_calls_for_raise_for_any_invalid_states(self, setup: Fixture):
            assert_has_calls_exactly(
                mock=setup.raise_for_any_invalid_states_mock, expected_calls=setup.expected_raise_for_any_invalid_states
            )

        def test_should_have_expected_calls_for_start_or_stop_instances(self, setup: Fixture):
            assert_has_calls_exactly(
                mock=setup.start_or_stop_instances_mock, expected_calls=setup.expected_start_or_stop_instances_calls
            )

    class TestStartOrStopInstances:
        mock_provider: Mock = Mock()

        @dataclass
        class Parameters:
            description: str
            operation: str
            wait: bool

            expected_start_instances_calls: list["call"] = field(default_factory=list)
            expected_stop_instances_calls: list["call"] = field(default_factory=list)

        @dataclass
        class Fixture:
            expected_start_instances_calls: list["call"]
            expected_stop_instances_calls: list["call"]

        @pytest.fixture(
            ids=lambda x: x.description,
            params=[
                Parameters(
                    description='"start" operation, no waiting',
                    operation="start",
                    wait=False,
                    expected_start_instances_calls=[call(["1", "2", "3"], wait=False)],
                ),
                Parameters(
                    description='"start" operation, with waiting',
                    operation="start",
                    wait=True,
                    expected_start_instances_calls=[call(["1", "2", "3"], wait=True)],
                ),
                Parameters(
                    description='"stop" operation, no waiting',
                    operation="stop",
                    wait=False,
                    expected_stop_instances_calls=[call(["1", "2", "3"], wait=False)],
                ),
                Parameters(
                    description='"stop" operation, with waiting',
                    operation="stop",
                    wait=True,
                    expected_stop_instances_calls=[call(["1", "2", "3"], wait=True)],
                ),
            ],
        )
        def setup(self, request):
            params: TestCommand.TestStartOrStopInstances.Parameters = request.param

            self.mock_provider.reset_mock()
            project_mock = create_mock_project()
            project_mock.provider = self.mock_provider

            # noinspection PyProtectedMember
            compute.Command._start_or_stop_instances(
                project_mock,
                instance_ids=["1", "2", "3"],
                operation=params.operation,
                wait=params.wait,
            )

            return self.Fixture(
                expected_start_instances_calls=params.expected_start_instances_calls,
                expected_stop_instances_calls=params.expected_stop_instances_calls,
            )

        def test_should_have_expected_calls_for_start_instances(self, setup: Fixture):
            assert_has_calls_exactly(
                mock=self.mock_provider.start_compute_instance, expected_calls=setup.expected_start_instances_calls
            )

        def test_should_have_expected_calls_for_stop_instances(self, setup: Fixture):
            assert_has_calls_exactly(
                mock=self.mock_provider.stop_compute_instance, expected_calls=setup.expected_stop_instances_calls
            )
