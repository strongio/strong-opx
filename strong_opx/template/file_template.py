import os

import jinja2

from strong_opx.config import opx_config
from strong_opx.template.context import Context
from strong_opx.template.template import Template
from strong_opx.utils.tracking import OpxString, Position, set_position


class FileTemplate:
    def __init__(self, file_path: str):
        self.file_path = file_path

    @property
    def content(self) -> str:
        with open(self.file_path) as f:
            return f.read()

    def render(self, context: Context) -> str:
        if opx_config.templating_engine == "jinja2":
            return self._render_with_jinja2(context)

        return self._default_renderer(context)

    def _default_renderer(self, context: Context) -> str:
        content = OpxString(self.content)
        set_position(content, self.file_path, Position(1, 1), None)
        return Template(content).render(context)

    def _render_with_jinja2(self, context: Context) -> str:
        loader = jinja2.FileSystemLoader(os.path.dirname(self.file_path))
        environment = jinja2.Environment(loader=loader)
        template = environment.from_string(self.content)
        return template.render(**context.as_dict())

    def render_to_file(self, target_path: str, context: Context) -> None:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w") as f:
            f.write(self.render(context))
