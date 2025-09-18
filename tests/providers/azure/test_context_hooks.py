import os
from unittest import TestCase
from unittest.mock import patch

from strong_opx.exceptions import ImproperlyConfiguredError
from strong_opx.providers.azure.context_hooks import update_environ_hook
from strong_opx.template import Context


@patch.dict("os.environ", clear=True)
class UpdateEnvironHookTests(TestCase):
    def test_sets_azure_environment_variables(self):
        context = Context(
            {
                "AZURE_SUBSCRIPTION_ID": "test-sub-id",
                "AZURE_RESOURCE_GROUP": "test-rg",
                "AZURE_CLIENT_ID": "test-client-id",
                "OTHER_KEY": "should_not_be_set",
            }
        )
        update_environ_hook(context)
        self.assertEqual(os.environ["AZURE_SUBSCRIPTION_ID"], "test-sub-id")
        self.assertEqual(os.environ["AZURE_RESOURCE_GROUP"], "test-rg")
        self.assertEqual(os.environ["AZURE_CLIENT_ID"], "test-client-id")
        self.assertNotIn("OTHER_KEY", os.environ)

    def test_missing_subscription_id_raises(self):
        context = Context({"AZURE_RESOURCE_GROUP": "test-rg"})
        with self.assertRaises(ImproperlyConfiguredError) as cm:
            update_environ_hook(context)

        self.assertIn("Azure Subscription ID is not configured", str(cm.exception))

    def test_missing_resource_group_raises(self):
        context = Context({"AZURE_SUBSCRIPTION_ID": "test-sub-id"})
        with self.assertRaises(ImproperlyConfiguredError) as cm:
            update_environ_hook(context)

        self.assertIn("Azure Resource Group is not configured", str(cm.exception))
