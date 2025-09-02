import unittest

from strong_opx import __version__
from strong_opx.codegen.project_generator import ProjectGenerator
from strong_opx.template import Context


class ProjectGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = ProjectGenerator("my_project", "/path/to/output")

    def test_get_output_dir(self):
        self.assertEqual(
            "/path/to/output",
            self.generator.get_output_dir(Context()),
        )

    def test_get_context(self):
        self.assertEqual(
            self.generator.get_context(Context()).as_dict(),
            {"project_name": "my_project", "strong_opx_version": __version__},
        )
