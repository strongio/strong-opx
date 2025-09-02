import contextlib
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock

from strong_opx.config import opx_config
from strong_opx.template import Context, FileTemplate


@contextlib.contextmanager
def override_templating_engine(engine):
    old_engine = opx_config.templating_engine
    opx_config.templating_engine = engine
    yield
    opx_config.templating_engine = old_engine


class FileTemplateTests(TestCase):
    DEFAULT_CONTEXT = Context({"VAR_1": "some-value"})

    def test_jinja2_engine(self):
        with override_templating_engine("jinja2"), tempfile.NamedTemporaryFile() as f:
            template = FileTemplate(f.name)
            template._render_with_jinja2 = renderer = MagicMock()
            template.render(self.DEFAULT_CONTEXT)

        renderer.assert_called_once_with(self.DEFAULT_CONTEXT)

    def test_basic_engine(self):
        with override_templating_engine("strong_opx"), tempfile.NamedTemporaryFile() as f:
            template = FileTemplate(f.name)
            template._default_renderer = renderer = MagicMock()
            template.render(self.DEFAULT_CONTEXT)

        renderer.assert_called_once_with(self.DEFAULT_CONTEXT)
