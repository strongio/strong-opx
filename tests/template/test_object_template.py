import copy
from typing import Any
from unittest import TestCase
from unittest.mock import Mock, create_autospec, patch

from parameterized import parameterized

from strong_opx.exceptions import UndefinedVariableError, VariableError
from strong_opx.template import Context
from strong_opx.template.object_template import ObjectTemplate, Substitution, TreeNode
from tests.helper_functions import patch_colorama


@patch_colorama
class ObjectTemplateTests(TestCase):
    @parameterized.expand(
        [
            # Mapping with strings
            ({"V1": "${VI}"}, {"V1": "i"}),
            ({"V1": "${VI}"}, {"V1": "i"}),
            ({"V1": "${V2}", "V2": "${VI}"}, {"V1": "i", "V2": "i"}),
            # Mapping with collections
            ({"V1": ["${VI}"]}, {"V1": ["i"]}),
            ({"V1": ["${VI}"], "V2": ["${V1}"]}, {"V1": ["i"], "V2": [["i"]]}),
            # Referring to an index of a collection
            ({"V1": ["${VSEQ[3]}", "${VSEQ[0]}"]}, {"V1": ["iv", "i"]}),
            # Mapping
            ({"V1": {"V2": "${VI}"}}, {"V1": {"V2": "i"}}),
            ({"V1": {"${V1}": "${VI}"}}, {"V1": {"${V1}": "i"}}),  # Keys shouldn't be resolved
            ({"V1": {"V2": "${VI}"}, "V3": {"V4": "${V1}"}}, {"V1": {"V2": "i"}, "V3": {"V4": {"V2": "i"}}}),
            # Nested mapping
            ({"V1": [{"V2": "${VI}"}]}, {"V1": [{"V2": "i"}]}),
            ({"V1": {"V2": ["${VI}"]}}, {"V1": {"V2": ["i"]}}),
            # Nested mapping
            ({"V1": '${VNESTED["VINNER"]}'}, {"V1": "inner"}),
            # String
            ("${VI}", "i"),
            ("no substitutions", "no substitutions"),
            # Non-string "raw" value
            (123, 123),
            # Collection
            (
                ["${VI}", 2, "three", {"four": '${VNESTED["VINNER"]}'}, "${VSEQ[3][1:]}"],
                ["i", 2, "three", {"four": "inner"}, "v"],
            ),
        ]
    )
    def test_render(self, value: dict[str, Any], expected_rendered_value: dict[str, Any]):
        original_context = {"VI": "i", "VSEQ": ["i", "ii", "iii", "iv"], "VNESTED": {"VINNER": "inner"}}
        context_backup = copy.deepcopy(original_context)

        context = Context(original_context)
        rendered_value = ObjectTemplate(context).render(value)

        self.assertEqual(expected_rendered_value, rendered_value)
        self.assertEqual(context.as_dict(), context_backup)  # context unchanged

    def test_unknown_variable(self):
        with self.assertRaises(UndefinedVariableError) as cm:
            ObjectTemplate(Context()).render({"V1": "${VI}"})

        self.assertEqual(cm.exception.names, ("VI",))

    def test_circular_dependency(self):
        with self.assertRaises(VariableError) as cm:
            ObjectTemplate(Context()).render({"V1": "${V2}", "V2": "${V1}"})

        self.assertEqual(
            "{Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}Found circular dependency: V1 -> " "V2 -> V1{Style.RESET_ALL}",
            str(cm.exception),
        )

    def test_deep_circular_dependency(self):
        with self.assertRaises(VariableError) as cm:
            ObjectTemplate(Context()).render({"V1": "${V2}", "V2": "${V3}", "V3": "${V4}", "V4": "${V1}"})

        self.assertEqual(
            (
                "{Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}Found circular dependency: V1 -> "
                "V2 -> V3 -> V4 -> V1{Style.RESET_ALL}"
            ),
            str(cm.exception),
        )

    def test_can_overwrite_not_frozen_variables(self):
        context = Context({"not_frozen": "mutable value"})

        rendered_value = ObjectTemplate(context).render(
            {
                "not_frozen": "steve",
                "uses_not_frozen": "blah ${not_frozen}",
            }
        )

        self.assertDictEqual(
            rendered_value,
            {
                "not_frozen": "steve",
                "uses_not_frozen": "blah steve",
            },
        )

    def test_can_locally_overwrite_initial_variables(self):
        context = Context({"frozen": "immutable value"}).chain()

        rendered_value = ObjectTemplate(context).render(
            {
                "frozen": "steve",
                "uses_overriden": "blah ${frozen}",
            }
        )

        self.assertEqual(
            rendered_value,
            {
                "frozen": "steve",
                "uses_overriden": "blah steve",
            },
        )

        # Value should not be changed in context
        self.assertEqual(context.get("frozen"), "immutable value")

    def test_can_overwrite_not_frozen_variables_complex(self):
        context = Context({"not_frozen": "mutable value"})

        # This test will pass if the 'not_frozen' comes before the 'uses_not_frozen' key
        rendered_value = ObjectTemplate(context).render(
            {"uses_not_frozen": "blah ${not_frozen}", "not_frozen": "${other} steve", "other": "other"}
        )

        self.assertDictEqual(
            rendered_value, {"not_frozen": "other steve", "uses_not_frozen": "blah other steve", "other": "other"}
        )

    def test_can_overwrite_not_frozen_variables_complex_nested(self):
        context = Context({"top": {"nested": "top.nested value"}})

        rendered_value = ObjectTemplate(context).render(
            {
                "top": {"nested": 'new top.nested value ${foo["baz"]}'},
                "foo": {"bar": '${top["nested"]} 2', "baz": "buzz"},
            }
        )

        self.assertDictEqual(
            rendered_value,
            {
                "top": {"nested": "new top.nested value buzz"},
                "foo": {"bar": "new top.nested value buzz 2", "baz": "buzz"},
            },
        )


class ResolveSubstitutionsNoDeadlock(TestCase):
    def setUp(self):
        self.handle_deadlock_patch = patch.object(ObjectTemplate, "handle_deadlock", autospec=True)
        self.handle_deadlock_mock = self.handle_deadlock_patch.start()

        self.context = create_autospec(spec=Context, instance=True)
        self.subject = ObjectTemplate(self.context)

        self.first_sub = create_autospec(spec=Substitution, instance=True)
        self.second_sub = create_autospec(spec=Substitution, instance=True)
        self.second_sub.can_resolve.return_value = True

        self.subject.substitutions = [
            self.first_sub,
            self.second_sub,
        ]

        self.subject.resolve_substitutions(self.context, False)

    def test_should_call_resolve_for_first_sub(self):
        self.first_sub.resolve.assert_called_once_with(self.context)

    def test_should_call_resolve_for_second_sub(self):
        self.second_sub.resolve.assert_called_once_with(self.context)

    def test_should_not_call_handle_deadlock(self):
        self.handle_deadlock_mock.assert_not_called()

    def test_should_remove_all_subs(self):
        self.assertEqual(self.subject.substitutions, [])

    def tearDown(self) -> None:
        self.handle_deadlock_patch.stop()


class ResolveSubstitutionsWithDeadlock(TestCase):
    def setUp(self):
        self.handle_deadlock_patch = patch.object(ObjectTemplate, "handle_deadlock", autospec=True)
        self.handle_deadlock_mock = self.handle_deadlock_patch.start()
        self.handle_deadlock_mock.side_effect = ValueError("got here")

        self.subject = ObjectTemplate(Context())

        # First sub can never render, so we will eventually call handle_deadlock()
        self.first_sub = create_autospec(spec=Substitution, instance=True)
        self.first_sub.can_resolve.return_value = False

        # Can render, so will be removed from self.substitutions when handle_deadlock() is called
        self.second_sub = create_autospec(spec=Substitution, instance=True)
        self.second_sub.can_resolve.return_value = True

        self.subject.substitutions = [
            self.first_sub,
            self.second_sub,
        ]

        try:
            self.subject.resolve_substitutions(self.subject.context, False)
        except ValueError as caught_error:
            self.caught_error = caught_error

    def test_should_not_call_resolve_for_first_sub(self):
        self.first_sub.resolve.assert_not_called()

    def test_should_call_handle_deadlock(self):
        self.handle_deadlock_mock.assert_called_once_with(self.subject, {self.second_sub.ref})

    def test_should_remove_subs_that_could_resolve(self):
        self.assertEqual(self.subject.substitutions, [self.first_sub])

    def test_should_have_expected_error(self):
        self.assertEqual("got here", str(self.caught_error))

    def tearDown(self) -> None:
        self.handle_deadlock_patch.stop()


class HandleDeadlock(TestCase):
    def test_should_raise_error_for_first_undefined_variable(self):
        subject = ObjectTemplate(Context())

        # Four unresolved, required variables, but will only raise for the first
        subject.substitutions = [
            create_autospec(spec=Substitution, instance=True, ref="the_root", required_refs={"one", "two"}),
            create_autospec(spec=Substitution, instance=True, ref="the_root", required_refs={"three", "four"}),
        ]

        with self.assertRaises(UndefinedVariableError) as cm:
            subject.handle_deadlock(set())

        # We cannot guarantee which of the undefined vars will be found first, so use a regex to check it's one of them
        # (We could guarantee order by sorting in the source code, but it's not necessary)
        self.assertRegex(str(cm.exception), r"(one|two|three|four) is undefined")

    @patch_colorama
    @patch.object(TreeNode, "check_cycle", autospec=True)
    def test_should_raise_for_circular_dependency(self, tree_node_check_cycle_mock: Mock):
        tree_node_check_cycle_mock.return_value = ["one", "two", "three"]

        subject = ObjectTemplate(Context())

        # This gets us past the check for undefined variables
        subject.substitutions = [
            create_autospec(spec=Substitution, instance=True, ref="first_root", required_refs={"first_root"}),
        ]

        with self.assertRaises(VariableError) as cm:
            subject.handle_deadlock(set())

        self.assertEqual(
            "{Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}Found circular dependency: "
            "three -> two -> one{Style.RESET_ALL}",
            str(cm.exception),
        )
