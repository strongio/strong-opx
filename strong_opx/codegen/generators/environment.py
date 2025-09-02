import os

from strong_opx.codegen.generator import TemplateGenerator
from strong_opx.codegen.questions import ChoiceQuestion, SimpleQuestion
from strong_opx.project import Environment
from strong_opx.template import Context


class Generator(TemplateGenerator):
    template_dir = "environment"

    questions = {
        "environment_name": SimpleQuestion(
            prompt="Specify environment name",
            validation_re=r"[A-Za-z][A-Za-z0-9-]",
        ),
        "aws_region": ChoiceQuestion(
            prompt="Specify AWS region",
            choices=[
                "us-east-1",
                "us-east-2",
                "us-west-1",
                "us-west-2",
            ],
        ),
    }

    def get_output_dir(self, context: "Context") -> str:
        return os.path.join(self.project.path, "environments", context["environment_name"])

    def get_context(self, context: "Context") -> "Context":
        context = super().get_context(context)
        context["environment"] = Environment(name=context["environment_name"], project=self.project, vars_={})

        self.project.provider.update_config({"region": context["aws_region"]})
        return context
