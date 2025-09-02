import os.path
import unittest
from unittest.mock import MagicMock, Mock, call, patch

from strong_opx.codegen.generator import BASE_TEMPLATE_DIR, CodeGenerator, TemplateGenerator
from strong_opx.codegen.questions import Question
from strong_opx.template import Context
from tests.mocks import create_mock_project


class CodeGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = MagicMock(spec=CodeGenerator, project=None, questions={})

    @patch("strong_opx.codegen.generator.Context")
    def test_generate_invoke_private_generate_func(self, context_mock):
        CodeGenerator.generate(self.generator)
        self.generator._generate.assert_called_once_with(
            self.generator.get_output_dir.return_value, context_mock.return_value
        )

    def test_generate_update_context_from_questions(self):
        q1 = MagicMock(spec=Question)
        q2 = MagicMock(spec=Question)

        q1.from_stdin.return_value = "q1 answer"
        q2.from_stdin.return_value = "q2 answer"

        self.generator.questions = {
            "q1": q1,
            "q2": q2,
        }

        CodeGenerator.generate(self.generator)
        context = self.generator._generate.call_args.args[1]

        self.assertEqual(context["q1"], "q1 answer")
        self.assertEqual(context["q2"], "q2 answer")


class TemplateGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.project = create_mock_project()
        self.generator = TemplateGenerator(project=self.project)
        self.generator.template_dir = "sample_template"

    @patch("os.listdir", MagicMock(return_value=["template1", "template2"]))
    @patch("os.path.isdir", MagicMock(return_value=True))
    def test_list_templates__only_directories(self):
        self.assertListEqual(["template1", "template2"], self.generator.list_templates())

    @patch("os.listdir", MagicMock(return_value=["template1", "template2"]))
    @patch("os.path.isdir", MagicMock(return_value=False))
    def test_list_templates__ignore_files(self):
        self.assertListEqual([], self.generator.list_templates())

    def test__generate_with_single_template(self):
        context = MagicMock()
        output_dir = MagicMock()
        generator = TemplateGenerator()
        generator.template_dir = "sample_template"
        generator.list_templates = MagicMock(return_value=["template1"])
        generator.render_template_dir = MagicMock()
        generator._generate(output_dir, context)
        generator.render_template_dir.assert_called_once_with("template1", output_dir, context)

    @patch("strong_opx.codegen.generator.select_prompt", return_value="template1")
    def test__generate_with_multi_template(self, select_prompt):
        context = MagicMock()
        output_dir = MagicMock()
        generator = TemplateGenerator()
        generator.template_dir = "sample_template"
        generator.list_templates = MagicMock(return_value=["template1", "template2"])
        generator.render_template_dir = MagicMock()
        generator._generate(output_dir, context)
        generator.render_template_dir.assert_any_call("template1", output_dir, context)
        self.assertEqual(generator.render_template_dir.call_count, 1)

    @patch("os.listdir")
    def test_iter_template_files(self, mock_listdir):
        mock_listdir.return_value = [
            "file1.txt",
            "file2.txt",
            "dir1/file3.txt",
            "dir1/file4.txt",
            "dir2/file5.txt",
        ]
        expected_output = [
            "file1.txt",
            "file2.txt",
            "dir1/file3.txt",
            "dir1/file4.txt",
            "dir2/file5.txt",
        ]
        self.assertListEqual(list(TemplateGenerator.iter_template_files("/path/to/base/dir")), expected_output)
        mock_listdir.assert_called_once_with("/path/to/base/dir")

    @patch("os.mkdir", new=MagicMock())
    @patch("shutil.copy")
    def test_render_template_dir__render_file_name(self, copy_mock: Mock):
        context = Context({"VAR1": "value1"})
        generator = TemplateGenerator()
        generator.template_dir = "sample_template"
        generator.iter_template_files = MagicMock(return_value=["{{ VAR1 }}.txt"])

        generator.render_template_dir("template1", "/path/to/output", context)
        copy_mock.assert_called_once_with(
            os.path.join(BASE_TEMPLATE_DIR, "sample_template", "template1", "{{ VAR1 }}.txt"),
            "/path/to/output/value1.txt",
        )

    @patch("os.mkdir", new=MagicMock())
    @patch("builtins.open")
    def test_render_template_dir__render_file_content(self, open_mock: Mock):
        context = Context({"VAR1": "value1"})
        generator = TemplateGenerator()
        generator.template_dir = "sample_template"
        generator.iter_template_files = MagicMock(return_value=["{{ VAR1 }}.txt-tpl"])

        generator.render_template_dir("template1", "/path/to/output", context)
        open_mock.assert_has_calls(
            [
                call(os.path.join(BASE_TEMPLATE_DIR, "sample_template", "template1", "{{ VAR1 }}.txt-tpl")),
                call("/path/to/output/value1.txt", "w"),
            ],
            any_order=True,
        )
