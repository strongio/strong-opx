from io import StringIO
from unittest import TestCase

from parameterized import parameterized

from strong_opx.hcl.extractor import FileReader, HCLVariableExtractor
from strong_opx.utils.tracking import Position, get_position


class FileReaderTests(TestCase):
    def test_discard_single_line_comment(self):
        s = StringIO('hello world\nvariable "hello"')
        reader = FileReader("some-file", s)
        reader.discard_single_line_comment()
        self.assertEqual(s.read(), 'variable "hello"')

    def test_discard_multi_line_comment(self):
        s = StringIO('hello world\n another line */\nvariable "hello"')
        reader = FileReader("some-file", s)
        reader.discard_multi_line_comment()
        self.assertEqual(s.read(), 'variable "hello"')

    def test_peak(self):
        s = StringIO("some content here")
        reader = FileReader("some-file", s)
        self.assertEqual("some", reader.peak(4))
        self.assertEqual(s.tell(), 0)

    def test_discard_whitespaces(self):
        s = StringIO(' \n\tvariable "hello"')
        reader = FileReader("some-file", s)
        reader.discard_whitespaces()
        self.assertEqual(s.read(), 'variable "hello"')

    @parameterized.expand(
        [
            ('hello"', "hello"),
            ('hello\\" world"', 'hello\\" world'),
        ]
    )
    def test_read_string(self, string, expected):
        reader = FileReader("some-file", StringIO(string))
        s = reader.read_string('"')
        self.assertEqual(expected, s)

    def test_read_until(self):
        s = StringIO('variable "AWS_REGION" {}')
        reader = FileReader("some-file", s)
        self.assertEqual('variable "AWS_REGION" {', reader.read_until("{"))

    @parameterized.expand(
        [
            ("\n} trailing text", "\n}"),  # trailing text excluded, because it is after }
            (
                "before nested { nested braces } after nested } trailing text",
                "before nested { nested braces } after nested }",  # trailing text excluded, because it is after }
            ),
            ("\n{ } }", "\n{ } }"),
            ("\n 1 # something with \n {\n }", "\n 1 \n {\n }"),
            ('\n "something with } or {" }', '\n "something with } or {" }'),
        ]
    )
    def test_read_block(self, string, expected):
        reader = FileReader("some-file", StringIO(string))
        self.assertEqual(expected, reader.read_block("{", "}"))


class HCLVariableExtractorTests(TestCase):
    def test_extract__optional(self):
        s = StringIO('variable "AWS_REGION" {\n     default = "us-west-2"\n}')
        extractor = HCLVariableExtractor()
        extractor.extract("some-file", s)
        self.assertSetEqual(extractor.optional_vars, {"AWS_REGION"})
        self.assertSetEqual(extractor.required_vars, set())

    def test_extract__required(self):
        s = StringIO('variable "AWS_REGION" {\n     description = "region-name"\n}')
        extractor = HCLVariableExtractor()
        extractor.extract("some-file", s)
        self.assertSetEqual(extractor.required_vars, {"AWS_REGION"})
        self.assertSetEqual(extractor.optional_vars, set())

    @parameterized.expand(
        [
            '// This is a comment\nvariable "var_name" {}',
            '# This is a comment\nvariable "var_name" {}',
            '/* This is a comment */\nvariable "var_name" {}',
            'variable "var_name" { // This is a comment\n}',
            'variable "var_name" { # This is a comment \n}',
            'variable "var_name" { /* This is a comment */ }',
        ]
    )
    def test_extract__preceding_comment(self, string):
        extractor = HCLVariableExtractor()
        extractor.extract("some-file", StringIO(string))

        self.assertSetEqual(extractor.required_vars, {"var_name"})

    def test_extracted_vars_has_position_markers(self):
        s = StringIO('variable "AWS_REGION" {}')
        extractor = HCLVariableExtractor()
        extractor.extract("some-file", s)

        var_ = extractor.required_vars.pop()
        file_path, start_pos, end_pos = get_position(var_)
        self.assertEqual("some-file", file_path)
        self.assertEqual(Position(1, 11), start_pos)
        self.assertEqual(Position(1, 21), end_pos)
