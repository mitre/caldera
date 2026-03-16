"""Tests that all plugins have a requirements.txt file."""
import os
import pytest

PLUGINS_DIR = 'plugins'


def _discover_plugins():
    """Return list of plugin names that have a hook.py (i.e., are real caldera plugins)."""
    if not os.path.isdir(PLUGINS_DIR):
        return []
    return [
        p for p in os.listdir(PLUGINS_DIR)
        if os.path.isfile(os.path.join(PLUGINS_DIR, p, 'hook.py'))
    ]


@pytest.mark.parametrize('plugin', _discover_plugins())
def test_plugin_has_requirements_txt(plugin):
    req_path = os.path.join(PLUGINS_DIR, plugin, 'requirements.txt')
    assert os.path.isfile(req_path), (
        'Plugin %s is missing requirements.txt at %s' % (plugin, req_path)
    )
