import argparse
import logging
from typing import Any

from strong_opx.management.command import ProjectCommand
from strong_opx.platforms import GenericPlatform
from strong_opx.project import Environment, Project
from strong_opx.providers.compute import ComputeInstance, ComputeInstanceState

logger = logging.getLogger(__name__)


class Command(ProjectCommand):
    help_text = "Manage state of compute instance inside a project/environment"
    examples = [
        "strong-opx ec2 --project <project> --env <env> stop 10.0.0.1 ...",
        "strong-opx ec2 --project <project> --env <env> start primary ...",
        "strong-opx ec2 --project <project> --env <env> stop primary:2 ...",
    ]

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("operation", help="Operation to execute", choices={"start", "stop", "restart", "status"})
        parser.add_argument("host_or_group", nargs="+", help="Hostname or host group or ip of instance")
        parser.add_argument("--wait", default=False, action="store_true", help="Wait for operation to complete")

    def handle(
        self,
        environment: Environment,
        project: Project,
        operation: str,
        host_or_group: list[str],
        wait: bool,
        **options: Any,
    ) -> None:
        platform = environment.select_platform(GenericPlatform)

        instances: list[ComputeInstance] = []
        for h in host_or_group:
            instances.extend(platform.resolve_instance(h))

        instance_states, running_instances, stopped_instances = self._sort_by_state(instances)

        if operation == "status":
            self._log_instance_states(instance_states, instances)
            return

        self._raise_for_any_invalid_states(instance_states)

        if operation in ("stop", "restart") and running_instances:
            # if restarting, we *need* to wait for instances to stop before we restart them
            wait_override = wait or operation == "restart"
            self._start_or_stop_instances(
                project=project, instance_ids=running_instances, operation="stop", wait=wait_override
            )

        if operation == "restart":
            stopped_instances.extend(running_instances)

        if operation in ("start", "restart") and stopped_instances:
            self._start_or_stop_instances(project=project, instance_ids=stopped_instances, operation="start", wait=wait)

    @staticmethod
    def _start_or_stop_instances(project: Project, instance_ids: list[str], operation: str, wait: bool):
        number_of_instances = len(instance_ids)
        logger.info(f'Executing "{operation}" operation for {number_of_instances} instance(s)...')

        if operation == "start":
            project.provider.start_compute_instance(instance_ids, wait=wait)
        elif operation == "stop":
            project.provider.stop_compute_instance(instance_ids, wait=wait)

        logger.info(f'"{operation}" operation complete for {number_of_instances} instance(s)')

    @staticmethod
    def _raise_for_any_invalid_states(instance_states: dict[ComputeInstance, ComputeInstanceState]):
        invalid_ips = []
        for ip, state in instance_states.items():
            if state not in (ComputeInstanceState.RUNNING, ComputeInstanceState.STOPPED):
                invalid_ips.append(f"(IP={ip}, State={state.value})")

        number_of_invalid_ips = len(invalid_ips)
        if number_of_invalid_ips > 0:
            raise RuntimeError(
                f'Found {number_of_invalid_ips} instance(s) with an invalid state: {", ".join(invalid_ips)}'
            )

    @staticmethod
    def _log_instance_states(
        instance_states: dict[ComputeInstance, ComputeInstanceState], instances: list[ComputeInstance]
    ):
        for instance in instances:
            logger.info(f"{instance.hostname} [{instance.instance_id}]: {instance_states[instance]}")

    @staticmethod
    def _sort_by_state(
        instances: list[ComputeInstance],
    ) -> tuple[dict[ComputeInstance, ComputeInstanceState], list[str], list[str]]:
        instance_states = {}
        stopped_instances = []
        running_instances = []

        for instance in instances:
            state = instance.current_state
            instance_states[instance] = state

            if state == ComputeInstanceState.RUNNING:
                running_instances.append(instance.instance_id)
            elif state == ComputeInstanceState.STOPPED:
                stopped_instances.append(instance.instance_id)

        return instance_states, running_instances, stopped_instances
