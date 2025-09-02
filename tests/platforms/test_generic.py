from unittest import TestCase

from strong_opx.platforms.generic import GenericPlatformConfig


class GenericPlatformConfigTests(TestCase):
    def test_select_direct_if_no_bastion(self):
        config = GenericPlatformConfig(hosts={"primary": ["8.8.8.8"]})

        self.assertEqual(config.ssh_method, "direct")

    def test_select_bastion_if_bastion_exists(self):
        config = GenericPlatformConfig(
            hosts={
                "bastion": ["8.8.8.8"],
                "primary": ["25.176.37.195"],
            }
        )

        self.assertEqual(config.ssh_method, "bastion")
