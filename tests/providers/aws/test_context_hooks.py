import os
from unittest import TestCase
from unittest.mock import patch

from parameterized import parameterized

from strong_opx.exceptions import ImproperlyConfiguredError
from strong_opx.providers.aws.context_hooks import import_and_clean_environ_hook, update_environ_hook
from strong_opx.template import Context


@patch.dict("os.environ", clear=True)
class ImportAndCleanEnvironHookTests(TestCase):
    @parameterized.expand(["some-profile", None])
    def test_import_and_clean_environ_hook(self, profile_name):
        os.environ["AWS_PROFILE"] = "test-profile"
        os.environ["AWS_ACCESS_KEY_ID"] = "test-access-key"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret-key"
        os.environ["AWS_SESSION_TOKEN"] = "test-session-token"
        os.environ["AWS_OTHER_ENV_VAR"] = "other-aws-env"
        os.environ["OTHER_ENV_VAR"] = "other-env"

        context = Context()
        if profile_name is not None:
            context["AWS_PROFILE"] = profile_name

        import_and_clean_environ_hook(context)

        if profile_name is None:
            self.assertEqual(context["AWS_PROFILE"], "test-profile")
            self.assertEqual(context["AWS_ACCESS_KEY_ID"], "test-access-key")
            self.assertEqual(context["AWS_SECRET_ACCESS_KEY"], "test-secret-key")
            self.assertEqual(context["AWS_SESSION_TOKEN"], "test-session-token")
        else:
            self.assertNotIn("AWS_PROFILE", os.environ)
            self.assertEqual(context["AWS_PROFILE"], profile_name)

            self.assertNotIn("AWS_ACCESS_KEY_ID", context)
            self.assertNotIn("AWS_ACCESS_KEY_ID", os.environ)

            self.assertNotIn("AWS_SECRET_ACCESS_KEY", context)
            self.assertNotIn("AWS_SECRET_ACCESS_KEY", os.environ)

            self.assertNotIn("AWS_SESSION_TOKEN", context)
            self.assertNotIn("AWS_SESSION_TOKEN", os.environ)

        self.assertIn("ACCOUNT_ID", context)
        self.assertNotIn("AWS_OTHER_ENV_VAR", os.environ)
        self.assertEqual(os.environ["OTHER_ENV_VAR"], "other-env")


@patch.dict("os.environ", clear=True)
class UpdateEnvironHookTests(TestCase):
    def test_update_environ_hook(self):
        context = Context(
            {
                "AWS_REGION": "test-region",
                "AWS_ACCESS_KEY_ID": "test-access-key",
                "AWS_SECRET_ACCESS_KEY": "test-secret-key",
                "OTHER_VAR": "other-var",
            }
        )

        update_environ_hook(context)

        self.assertEqual(os.environ["AWS_DEFAULT_REGION"], "test-region")
        self.assertEqual(os.environ["AWS_ACCESS_KEY_ID"], "test-access-key")
        self.assertEqual(os.environ["AWS_SECRET_ACCESS_KEY"], "test-secret-key")
        self.assertNotIn("OTHER_VAR", os.environ)

    def test_missing_aws_region(self):
        context = Context()

        with self.assertRaisesRegex(ImproperlyConfiguredError, "AWS Region is not configured"):
            update_environ_hook(context)
