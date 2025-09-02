import datetime
import sys
from unittest import TestCase

from parameterized import parameterized

from strong_opx.exceptions import TemplateError, UndefinedVariableError
from strong_opx.template import Context, Template
from strong_opx.utils.tracking import OpxString, Position, set_position

PY3_10_PLUS = sys.version_info[:2] >= (3, 10)


class TemplateTest(TestCase):
    context1 = Context({"username": "strong", "dt": datetime.datetime(2023, 1, 1)})

    context2 = Context(
        {
            "VAR_1": "value-1",
            "VAR_2": "value-2",
            "VAR_3": "value-3",
            "VAR_4": "value-4",
        }
    )

    def test_expression(self):
        t = Template("Hello {{ username }}!")
        rendered = t.render(self.context1)

        self.assertEqual(rendered, "Hello strong!")

    def test_expression_invalid_varname(self):
        with self.assertRaises(TemplateError) as cm:
            Template("Hello {{ 3rd }}!")

        if PY3_10_PLUS:
            # In case of python 3.10+, `3rd` is reported as invalid variable but in
            # older versions, `rd` is reported as invalid postfix for number. Thus,
            # there is a difference in Position
            self.assertEqual(cm.exception.errors[0].start_pos, Position(1, 10))
        else:
            self.assertEqual(cm.exception.errors[0].start_pos, Position(1, 11))

    def test_expression__filters(self):
        t = Template("Hello {{ username|titlecase }}!")
        rendered = t.render(self.context1)

        self.assertEqual(rendered, "Hello Strong!")

    def test_expression__invalid_filter(self):
        with self.assertRaises(TemplateError) as cm:
            Template("Hello {{ username|unknown_filter }}!")

        self.assertEqual(cm.exception.errors[0].error, "Unknown filter: unknown_filter")
        self.assertEqual(cm.exception.errors[0].start_pos, Position(1, 19))
        self.assertEqual(cm.exception.errors[0].end_pos, Position(1, 33))

    def test_expression__filter_args(self):
        t = Template('Today is {{ dt|datetime:"%Y-%m-%d" }}.')
        rendered = t.render(self.context1)

        self.assertEqual(rendered, "Today is 2023-01-01.")

    def test_expression__invalid_filter_args(self):
        with self.assertRaises(TemplateError) as cm:
            Template('Today is {{ dt|datetime:"%Y-%m-%d":12 }}.')

        self.assertEqual(cm.exception.errors[0].error, "Invalid Syntax")

    @parameterized.expand(
        [
            ("${VAR_1}", "value-1"),
            ("${VAR_1} ${VAR_2}", "value-1 value-2"),
            ("${{VAR_1}}", "${VAR_1}"),
            ("${VAR_1}}", "${VAR_1}}"),
            ("${{VAR_1}", "${{VAR_1}"),
        ]
    )
    def test_legacy_render(self, expression, expected_output):
        result = Template(expression).render(self.context2)
        self.assertEqual(result, expected_output)

    def test_action_tag__if(self):
        t = Template("{% if True %}true{% endif %}")
        rendered = t.render(self.context1)

        self.assertEqual(rendered, "true")

    def test_action_tag__if_false(self):
        t = Template("{% if False %}false{% endif %}")
        rendered = t.render(self.context1)

        self.assertEqual(rendered, "")

    def test_action_tag__if_else_true(self):
        t = Template("{% if username %}{{ username }}{% else %}{{ dt }}{% endif %}")
        rendered = t.render(self.context1)

        self.assertEqual("strong", rendered)

    def test_action_tag__if_else_false(self):
        t = Template("{% if False %}{{ username }}{% else %}{{ dt }}{% endif %}")
        rendered = t.render(self.context1)

        self.assertEqual("2023-01-01 00:00:00", rendered)

    def test_action_tag__for_else(self):
        with self.assertRaises(TemplateError) as cm:
            Template("{% for i in range(10) %}{{ i }}{% else %}{{ i * 10 }}{% endfor %}")

    def test_action_tag__for(self):
        t = Template("{% for i in range(10) %}{{ i }} {% endfor %}")
        rendered = t.render(self.context1)

        self.assertEqual(rendered, "0 1 2 3 4 5 6 7 8 9 ")

    def test_action_tag__missing_end(self):
        with self.assertRaises(TemplateError) as cm:
            Template("{% if some_something %}false")

        self.assertEqual(cm.exception.errors[0].error, "Unclosed tags: if")

    def test_action_tag__raw(self):
        t = Template("{% raw %}{{ i }}{% endraw %}")
        rendered = t.render(self.context1)

        self.assertEqual(rendered, "{{ i }}")

    def test_action_tag__nested_raw(self):
        t = Template("{% raw %}{% raw %}{{ i }}{% endraw %}{% endraw %}")
        rendered = t.render(self.context1)

        self.assertEqual(rendered, "{% raw %}{{ i }}{% endraw %}")

    def test_action_tag__action_tag_inside_raw(self):
        t = Template("{% raw %}{% if %}{% endif %}{% endraw %}")
        rendered = t.render(self.context1)

        self.assertEqual(rendered, "{% if %}{% endif %}")

    def test_action_tag__raw_additional_args(self):
        with self.assertRaises(TemplateError) as cm:
            Template("{% raw something %}some value{% endraw %}")

        self.assertEqual(cm.exception.errors[0].error, "raw action tag does not take any argument")

    def test_missing_key(self):
        with self.assertRaises(UndefinedVariableError):
            Template("${VAR_5}").render(self.context2)

    def test_missing_key__with_position(self):
        value = OpxString("${VAR_5}")
        set_position(value, "some-file", Position(1, 10), Position(1, 10 + len(value)))

        with self.assertRaises(UndefinedVariableError) as cm:
            Template(value).render(self.context2)

        self.assertEqual(cm.exception.names, ("VAR_5",))
        self.assertEqual(cm.exception.errors[0].file_path, "some-file")
        self.assertEqual(cm.exception.errors[0].start_pos, Position(1, 12))
        self.assertEqual(cm.exception.errors[0].end_pos, Position(1, 17))

    def test_missing_key__multiline_with_position(self):
        value = OpxString("line before\n${VAR_5}\nline after")
        set_position(value, "some-file", Position(1, 11), Position(3, 11))

        with self.assertRaises(UndefinedVariableError) as cm:
            Template(value).render(self.context2)

        self.assertEqual(cm.exception.names, ("VAR_5",))
        self.assertEqual(cm.exception.errors[0].file_path, "some-file")
        self.assertEqual(cm.exception.errors[0].start_pos, Position(2, 3))
        self.assertEqual(cm.exception.errors[0].end_pos, Position(2, 8))

    def test_render_non_string(self):
        t = Template("{{ dt }}")
        rendered = t.render(self.context1)

        self.assertEqual(rendered, self.context1["dt"])

    def test_comment(self):
        t = Template("Hello {# This is a comment #}")
        rendered = t.render(self.context1)

        self.assertEqual(rendered, "Hello ")

    def test_args_to_action_tag_end(self):
        with self.assertRaises(TemplateError) as cm:
            Template("{% if some_something %}false{% endif some_something %}")

        self.assertEqual(cm.exception.errors[0].error, "End block does not take any argument")

    def test_more_action_tag_end_blocks(self):
        with self.assertRaises(TemplateError) as cm:
            Template("{% if some_something %}false{% endif %}{% endfor %}")

        self.assertEqual(cm.exception.errors[0].error, "Unexpected end block")

    def test_different_end_block(self):
        with self.assertRaises(TemplateError) as cm:
            Template("{% if some_something %}false{% endfor %}")

        self.assertEqual(cm.exception.errors[0].error, "Expecting endif block, got endfor")

    def test_action_tag__unknown(self):
        with self.assertRaises(TemplateError) as cm:
            Template("{% block %}some-block{% endblock %}")

        self.assertEqual(cm.exception.errors[0].error, "Unknown action tag: block")

    def test_action_tag_unexpected_end_block(self):
        with self.assertRaises(TemplateError) as cm:
            Template("{% endif %}")

        self.assertEqual(cm.exception.errors[0].error, "Unexpected end block")
