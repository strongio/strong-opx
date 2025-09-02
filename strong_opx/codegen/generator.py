import os
import shutil
from typing import Generator

from strong_opx.codegen.questions import Question
from strong_opx.project import Project
from strong_opx.template import Context, FileTemplate, Template
from strong_opx.utils.prompt import select_prompt

TEMPLATE_POSTFIX = "-tpl"
BASE_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


class CodeGenerator:
    questions: dict[str, Question] = {}

    def __init__(self, project: "Project" = None):
        self.project = project

    def get_output_dir(self, context: "Context") -> str:
        raise NotImplementedError()

    def generate(self) -> None:
        context = Context({"project": self.project})
        for name, question in self.questions.items():
            context[name] = question.from_stdin()

        output_dir = self.get_output_dir(context)
        self._generate(output_dir, context)

    def _generate(self, output_dir: str, context: Context) -> None:
        raise NotImplementedError()


class TemplateGenerator(CodeGenerator):
    template_dir: str

    def get_context(self, context: "Context") -> "Context":
        context["project"] = self.project
        return context

    def list_templates(self) -> list[str]:
        template_dir = os.path.join(BASE_TEMPLATE_DIR, self.template_dir)

        return [d for d in os.listdir(template_dir) if os.path.isdir(os.path.join(template_dir, d))]

    def _generate(self, output_dir: str, context: Context) -> None:
        all_templates = self.list_templates()
        if len(all_templates) == 1:
            template_name = all_templates[0]
        else:
            template_name = select_prompt("Select Template", all_templates)

        self.render_template_dir(template_name, output_dir, context)

    def render_template_dir(self, template_name: str, output_dir: str, context: Context) -> None:
        context = self.get_context(context)
        template_dir = os.path.join(BASE_TEMPLATE_DIR, self.template_dir, template_name)

        for template_file in self.iter_template_files(template_dir):
            target_path = os.path.join(output_dir, Template(template_file).render(context))

            if template_file.endswith(TEMPLATE_POSTFIX):
                template = FileTemplate(os.path.join(template_dir, template_file))
                template.render_to_file(target_path[: -len(TEMPLATE_POSTFIX)], context)
            else:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy(
                    os.path.join(template_dir, template_file),
                    target_path,
                )

    @staticmethod
    def iter_template_files(base_path: str) -> Generator[str, None, None]:
        dirs = [base_path]

        while dirs:
            directory = dirs.pop()
            for filename in os.listdir(directory):
                full_path = os.path.join(directory, filename)
                if os.path.isdir(full_path):
                    dirs.append(full_path)
                else:
                    yield os.path.relpath(full_path, base_path)
