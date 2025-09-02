import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from strong_opx.project import Project
    from strong_opx.template import Context


class EnvironHook:
    def __init__(self, prefix: str):
        if not prefix:
            raise ValueError("prefix cannot be blank")

        self.prefix = prefix

    def __call__(self, context: "Context"):
        for k in os.environ:
            if k.startswith(self.prefix):
                context[k] = os.environ[k]


class ProjectContextHook:
    def __init__(self, project: "Project"):
        self.project = project

    def __call__(self, context: "Context"):
        context["SSH_KEY"] = lambda: self.project.config.ssh_key
        context["SSH_USER"] = lambda: self.project.config.ssh_user
