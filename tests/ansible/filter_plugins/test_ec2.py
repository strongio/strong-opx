import os
from unittest import TestCase, mock

import boto3
from moto import mock_aws

from strong_opx.ansible.filter_plugins.ec2 import FilterModule


@mock_aws
@mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-1"})
class SecurityGroupIdTests(TestCase):
    def test_no_match(self):
        sg_id = FilterModule().security_group_id("some-sg", "some-vpc")
        self.assertIsNone(sg_id)

    def test_single_sg_in_vpc(self):
        ec2 = boto3.client("ec2")
        expected_sg_id = ec2.create_security_group(GroupName="some-sg", Description="some-sg", VpcId="some-vpc")[
            "GroupId"
        ]

        actual_sg_id = FilterModule().security_group_id("some-sg", "some-vpc")
        self.assertEqual(expected_sg_id, actual_sg_id)

    def test_same_sg_in_multiple_vpc(self):
        ec2 = boto3.client("ec2")
        expected_sg_ids = [
            ec2.create_security_group(GroupName="some-sg", Description="some-sg", VpcId=f"vpc-{i}")["GroupId"]
            for i in range(3)
        ]

        actual_sg_id = FilterModule().security_group_id("some-sg", "vpc-1")
        self.assertEqual(actual_sg_id, expected_sg_ids[1])

    def test_sg_without_vpc_id(self):
        ec2 = boto3.client("ec2")
        expected_sg_id = ec2.create_security_group(GroupName="some-sg", Description="some-sg", VpcId="some-vpc")[
            "GroupId"
        ]

        actual_sg_id = FilterModule().security_group_id("some-sg", None)
        self.assertEqual(expected_sg_id, actual_sg_id)

    def test_conflicting_sg_without_vpc_id(self):
        ec2 = boto3.client("ec2")
        for i in range(3):
            ec2.create_security_group(GroupName="some-sg", Description="some-sg", VpcId=f"vpc-{i}")

        actual_sg_id = FilterModule().security_group_id("some-sg", None)
        self.assertIsNone(actual_sg_id)
