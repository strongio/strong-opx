from unittest import mock

import pytest

from strong_opx.exceptions import PluginError
from strong_opx.platforms.plugins import PlatformPlugin


def test_run_op_if_not_installed():
    plugin = mock.MagicMock(spec=PlatformPlugin)
    plugin.is_installed.return_value = False

    with pytest.raises(PluginError, match="not installed"):
        PlatformPlugin.run(plugin, "op")


def test_run_op_if_installed():
    plugin = mock.MagicMock(spec=PlatformPlugin, platform=mock.MagicMock())
    plugin.is_installed.return_value = True

    PlatformPlugin.run(plugin, "op")
    plugin.handle.assert_called_once_with()


def test_run_install_if_installed():
    plugin = mock.MagicMock(spec=PlatformPlugin, platform=mock.MagicMock())
    plugin.is_installed.return_value = True

    with pytest.raises(PluginError, match="already installed"):
        PlatformPlugin.run(plugin, "install")


def test_run_install_if_not_installed():
    plugin = mock.MagicMock(spec=PlatformPlugin, platform=mock.MagicMock())
    plugin.is_installed.return_value = False

    PlatformPlugin.run(plugin, "install")
    plugin.install.assert_called_once()
