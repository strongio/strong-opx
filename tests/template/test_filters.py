from unittest import TestCase

from strong_opx.template import Context, Template
from strong_opx.template.filters import base64_filter


class TemplateFilterTests(TestCase):
    def test_base64_filter(self):
        self.assertEqual(base64_filter("test"), "dGVzdA==")

    def test_base64_filter_inside_template(self):
        rendered = Template('{{ "test"|base64 }}').render(Context())

        self.assertEqual(rendered, "dGVzdA==")
