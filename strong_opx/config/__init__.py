import os

from strong_opx.config.base import Config, SystemConfig
from strong_opx.config.hierarchical import HierarchicalConfig
from strong_opx.config.opx import DEFAULT_TEMPLATING_ENGINE, StrongOpxConfig

PROJECT_CONFIG_FILE = "strong-opx.yml"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(os.path.realpath(__file__))))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
ANSIBLE_FILTER_PLUGINS = os.path.join(BASE_DIR, "ansible", "filter_plugins")

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".strong-opx")
CACHE_DIR = os.path.join(CONFIG_DIR, "cache")

system_config = SystemConfig(os.path.join(CONFIG_DIR, "config"))
opx_config = StrongOpxConfig()
