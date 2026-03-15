"""Tests that all plugins have a requirements.txt file."""
import os
import pytest

PLUGINS_DIR = os.path.join('plugins')

EXPECTED_PLUGINS = [
    'access', 'atomic', 'compass', 'debrief', 'emu', 'fieldmanual',
    'gameboard', 'human', 'magma', 'manx', 'response', 'sandcat',
    'ssl', 'stockpile', 'training', 'turla',
]


@pytest.mark.parametrize('plugin', EXPECTED_PLUGINS)
def test_plugin_has_requirements_txt(plugin):
    req_path = os.path.join(PLUGINS_DIR, plugin, 'requirements.txt')
    assert os.path.isfile(req_path), (
        'Plugin %s is missing requirements.txt at %s' % (plugin, req_path)
    )
