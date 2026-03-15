import os
import tempfile
import pytest
from app.utility.base_world import BaseWorld


class TestYamlSafeLoader:
    def test_loads_basic_yaml(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write('key: value\nnumber: 42\n')
            f.flush()
            result = BaseWorld.strip_yml(f.name)
            assert result == [{'key': 'value', 'number': 42}]
            os.unlink(f.name)

    def test_loads_list_yaml(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write('items:\n- one\n- two\n- three\n')
            f.flush()
            result = BaseWorld.strip_yml(f.name)
            assert result == [{'items': ['one', 'two', 'three']}]
            os.unlink(f.name)

    def test_none_path_returns_empty(self):
        result = BaseWorld.strip_yml(None)
        assert result == []

    def test_rejects_unsafe_yaml_construct(self):
        """SafeLoader should reject Python-specific YAML tags."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write('!!python/object/apply:os.system ["echo pwned"]\n')
            f.flush()
            with pytest.raises(Exception):
                BaseWorld.strip_yml(f.name)
            os.unlink(f.name)
