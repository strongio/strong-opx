import os
from unittest import TestCase, mock
from unittest.mock import patch

from strong_opx.project.context_hooks import EnvironHook, ProjectContextHook
from strong_opx.template import Context
from tests.mocks import create_mock_project


class SystemContextHookTests(TestCase):
    def setUp(self):
        self.prefix = "TEST_PREFIX"
        self.hook = EnvironHook(self.prefix)

    def test_prefix_blank(self):
        with self.assertRaises(ValueError):
            EnvironHook("")

    @patch.dict(os.environ, {"TEST_PREFIX_KEY1": "value1", "TEST_PREFIX_KEY2": "value2"})
    def test_call(self):
        context = Context()
        self.hook(context)

        self.assertEqual(context["TEST_PREFIX_KEY1"], "value1")
        self.assertEqual(context["TEST_PREFIX_KEY2"], "value2")

    @patch.dict(os.environ, {"TEST_PREFIX_KEY1": "value1", "TEST_PREFIX_KEY2": "value2", "OTHER_PREFIX_KEY": "other"})
    def test_call_ignores_other_prefix(self):
        context = Context()
        self.hook(context)

        self.assertEqual(context["TEST_PREFIX_KEY1"], "value1")
        self.assertEqual(context["TEST_PREFIX_KEY2"], "value2")
        self.assertFalse("OTHER_PREFIX_KEY" in context)


class ProjectContextHookTests(TestCase):
    def setUp(self):
        self.aws = mock.MagicMock()
        self.project = create_mock_project(config=mock.MagicMock(), aws=self.aws)
        self.hook = ProjectContextHook(self.project)

    def test_ssh_config(self):
        context = Context()

        self.project.config.ssh_key = "some-ssh-key"
        self.project.config.ssh_user = "some-ssh-user"
        self.hook(context)

        self.assertEqual(context["SSH_KEY"], "some-ssh-key")
        self.assertEqual(context["SSH_USER"], "some-ssh-user")
