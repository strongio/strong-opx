from typing import Optional

import boto3


class FilterModule:
    def __init__(self):
        self.client = boto3.client("ec2")

    def filters(self):
        return {
            "security_group_id": self.security_group_id,
            "ec2_public_ip": self.public_ip,
            "ec2_private_ip": self.private_ip,
            "vpc_id": self.vpc_id,
        }

    def security_group_id(self, sg_name: str, vpc_id: Optional[str]) -> Optional[str]:
        filters = [{"Name": "group-name", "Values": [sg_name]}]
        if vpc_id:
            filters.append({"Name": "vpc-id", "Values": [vpc_id]})

        response = self.client.describe_security_groups(Filters=filters)["SecurityGroups"]
        if len(response) == 1:
            return response[0]["GroupId"]

    def describe_instance(self, instance_name: str) -> dict:
        reservations = self.client.describe_compute_instance(Filters=[{"Name": "tag:Name", "Values": [instance_name]}])[
            "Reservations"
        ]

        instances = []
        for reservation in reservations:
            instances.extend(reservation["Instances"])

        if len(instances) == 0:
            raise ValueError(f"Unable to find instance with name: {instance_name}")

        if len(instances) > 1:
            raise ValueError(f"Found multiple instances with name: {instance_name}")

        return instances[0]

    def public_ip(self, instance_name: str) -> str:
        instance = self.describe_instance(instance_name)
        ip_address = instance.get("PublicIpAddress")
        if not ip_address:
            raise ValueError(f"Instance {instance_name} does not have a public IP")

        return ip_address

    def private_ip(self, instance_name: str) -> str:
        instance = self.describe_instance(instance_name)
        return instance["PrivateIpAddress"]

    def vpc_id(self, vpc_name: str, cidr_block: str = None) -> str:
        filters = [{"Name": "tag:Name", "Values": [vpc_name]}]
        if cidr_block:
            filters.append({"Name": "cidr-block-association.cidr-block", "Values": [cidr_block]})

        vpcs = self.client.describe_vpcs(Filters=filters, MaxResults=2)["Vpcs"]
        if len(vpcs) == 1:
            return vpcs[0]["VpcId"]

        raise ValueError(f"Found multiple VPCs with name: {vpc_name}. Specify a CIDR block to disambiguate")
