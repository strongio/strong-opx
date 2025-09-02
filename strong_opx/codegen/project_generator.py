from strong_opx import __version__
from strong_opx.codegen.generator import TemplateGenerator
from strong_opx.template import Context


class ProjectGenerator(TemplateGenerator):
    template_dir = "project"

    def __init__(self, name: str, output_dir: str):
        self.name = name
        self.output_dir = output_dir
        super().__init__()

    def get_output_dir(self, context: "Context") -> str:
        return self.output_dir

    def get_context(self, context: "Context") -> "Context":
        context.update({"project_name": self.name, "strong_opx_version": __version__})
        return context
