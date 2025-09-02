from unittest import TestCase, mock

from strong_opx.exceptions import UndefinedVariableError, VariableError
from strong_opx.template import Context


class ContextTests(TestCase):
    def test_lazy_evaluation(self):
        resolver = mock.Mock(return_value="some-value")

        context = Context({"key-a": resolver})
        resolver.assert_not_called()

        # Get value multiple times, but should be resolved only once
        self.assertEqual(context["key-a"], "some-value")
        self.assertEqual(context["key-a"], "some-value")
        resolver.assert_called_once()

    def test_chain(self):
        context_a = Context({"key-a": "a", "key-b": "b"})
        context_b = context_a.chain()

        context_a["key-a"] = "a-updated"
        self.assertEqual(context_b["key-a"], "a")
        self.assertEqual(context_a["key-a"], "a-updated")

    def test_nested_chain(self):
        context_a = Context({"key-a": "a", "key-b": "b"})
        context_b = context_a.chain()
        context_b["key-c"] = "c"

        context_c = context_b.chain()
        self.assertEqual(context_c.initial_vars, {"key-a", "key-b"})

    def test_nested_chain_update(self):
        """
        This test demonstrates how updates to parent contexts cause their old value to be propagated to child contexts.
        """
        context_a = Context({"key-a": "a", "key-b": "b"})
        context_b = context_a.chain()
        context_c = context_b.chain()
        context_a["key-a"] = "alpha"  # old 'a' value will be propagated to context_b and context_c
        context_b["key-b"] = "bravo"  # old 'b' value will be propagated to context_c

        self.assertDictEqual(context_a.as_dict(), {"key-a": "alpha", "key-b": "b"})
        self.assertDictEqual(context_b.as_dict(), {"key-a": "a", "key-b": "bravo"})
        self.assertDictEqual(context_c.as_dict(), {"key-a": "a", "key-b": "b"})

    def test_initial_vars_after_update(self):
        """
        This test demonstrates that initial_vars are calculated and Updates to the parent/root context will
        always appear in the initial_vars of the child context.
        """
        context_a = Context({"key-a": "a", "key-b": "b"})
        context_b = context_a.chain()
        context_a["key-c"] = "c"

        self.assertDictEqual(context_a.as_dict(), {"key-a": "a", "key-b": "b", "key-c": "c"})
        self.assertEqual(context_b.initial_vars, {"key-a", "key-b", "key-c"})

    def test_as_dict(self):
        context = Context(
            {
                "key-a": mock.Mock(return_value="a"),
                "key-b": "b",
            }
        )

        self.assertDictEqual(context.as_dict(), {"key-a": "a", "key-b": "b"})

    def test_as_dict__non_initial_vars(self):
        context_a = Context({"key-a": "a", "key-b": "b"})
        context_b = context_a.chain()

        context_b["key-c"] = mock.Mock(return_value="c")
        context_b["key-d"] = "d"

        self.assertDictEqual(context_b.as_dict(exclude_initial=True), {"key-c": "c", "key-d": "d"})

    def test_as_dict__all_vars(self):
        context_a = Context({"key-a": "a", "key-b": "b"})
        context_b = context_a.chain()

        context_b["key-c"] = mock.Mock(return_value="c")
        context_b["key-d"] = "d"

        self.assertDictEqual(
            context_b.as_dict(exclude_initial=False),
            {
                "key-a": "a",
                "key-b": "b",
                "key-c": "c",
                "key-d": "d",
            },
        )

    def test_require_all_known(self):
        context = Context({"key-a": "a", "key-b": mock.Mock(return_value="b"), "key-c": "c"})
        result = context.require("key-a", "key-b")
        self.assertDictEqual(result, {"key-a": "a", "key-b": "b"})

    def test_require_unknown(self):
        context = Context({"key-a": "a", "key-b": mock.Mock(return_value="b"), "key-c": "c"})

        with self.assertRaises(UndefinedVariableError) as cm:
            context.require("key-a", "key-b", "key-d", "key-f")

        self.assertEqual(("key-d", "key-f"), cm.exception.names)

    def test_delete_should_raise_error(self):
        context = Context({"key-a": "a", "key-b": "b"})

        with self.assertRaises(NotImplementedError):
            del context["key-a"]

    def test_pop_should_raise_error(self):
        context = Context({"key-a": "a", "key-b": "b"})

        with self.assertRaises(NotImplementedError):
            context.pop("key-a")
