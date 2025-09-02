import boto3

from strong_opx.providers.compute import ComputeInstanceDescription, ComputeInstanceState
from strong_opx.utils.mapping import CaseInsensitiveMultiTagDict


def transform_instance(instance: dict) -> ComputeInstanceDescription:
    tags = CaseInsensitiveMultiTagDict()
    for tag in instance.get("Tags", []):
        tags[tag["Key"]] = tag["Value"]

    try:
        state = ComputeInstanceState(instance["State"]["Name"])
    except ValueError:
        state = ComputeInstanceState.UNKNOWN

    return ComputeInstanceDescription(
        instance_id=instance["InstanceId"],
        state=state,
        public_ip=instance.get("PublicIpAddress"),
        private_ip=instance.get("PrivateIpAddress"),
        tags=tags,
    )


def describe_instances(**kwargs) -> list[ComputeInstanceDescription]:
    response = boto3.client("ec2").describe_instances(**kwargs)

    instances = []
    for reservation in response["Reservations"]:
        for instance in reservation.get("Instances", []):
            if instance["State"]["Name"] == "terminated":
                continue  # Skip terminated instances

            instances.append(transform_instance(instance))

    return instances
