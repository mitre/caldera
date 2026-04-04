"""
Tests for ability YAML correctness.

Regression test for issue #3097: extra semicolon in ip-neighbour discovery
ability command (ability id f489321f31b6ef36304294562d3d4645).
"""
import os
import re

import yaml


ABILITY_ID_IP_NEIGHBOUR = 'f489321f31b6ef36304294562d3d4645'

# Locate the repo root relative to this file's location so tests work
# regardless of the current working directory.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# The YAML file lives under data/abilities/discovery/ in the main repo tree.
DISCOVERY_DIR = os.path.join(
    REPO_ROOT,
    'data', 'abilities', 'discovery',
)


def _load_ability_yaml(ability_id):
    """Return a (data, path) tuple for the given ability id YAML file.

    ``data`` is the parsed YAML list, or ``None`` if the file cannot be parsed
    or does not exist.  ``path`` is always the expected filesystem path.
    """
    path = os.path.join(DISCOVERY_DIR, f'{ability_id}.yml')
    if not os.path.isfile(path):
        return None, path
    with open(path, 'r', encoding='utf-8') as fh:
        return yaml.safe_load(fh), path


class TestIpNeighbourAbility:
    """Regression tests for ability f489321f31b6ef36304294562d3d4645."""

    def test_ability_yaml_file_exists(self):
        """The ip-neighbour ability YAML file must be present."""
        _, path = _load_ability_yaml(ABILITY_ID_IP_NEIGHBOUR)
        assert os.path.isfile(path), (
            f"Ability YAML not found at {path}. "
            "Ensure the file exists under data/abilities/discovery/."
        )

    def test_no_extra_semicolon_in_command(self):
        """Command field must not contain a stray '; ;' or ';  ;' sequence (issue #3097)."""
        data, path = _load_ability_yaml(ABILITY_ID_IP_NEIGHBOUR)
        assert data is not None, f"Could not parse YAML at {path}"

        for entry in data:
            platforms = entry.get('platforms', {})
            for platform, executors in platforms.items():
                for executor_name, executor_def in executors.items():
                    command = executor_def.get('command', '')
                    assert not re.search(r';\s+;', command), (
                        f"Ability {ABILITY_ID_IP_NEIGHBOUR} ({platform}/{executor_name}) "
                        f"contains an extra semicolon sequence in command: {command!r}"
                    )

    def test_command_ends_with_ip_neighbour_show(self):
        """The fixed command must end with 'ip neighbour show'."""
        data, path = _load_ability_yaml(ABILITY_ID_IP_NEIGHBOUR)
        assert data is not None, f"Could not parse YAML at {path}"

        for entry in data:
            platforms = entry.get('platforms', {})
            linux = platforms.get('linux', {})
            sh = linux.get('sh', {})
            command = sh.get('command', '')
            assert command.strip().endswith('ip neighbour show'), (
                f"Expected command to end with 'ip neighbour show', got: {command!r}"
            )
