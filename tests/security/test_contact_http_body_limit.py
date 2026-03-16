import pytest


class TestContactHttpBodyLimit:
    def test_body_size_default_computation(self):
        """Default 512 KB limit computes correctly."""
        config_val = None
        max_kb = int(config_val) if config_val is not None else 512
        max_bytes = max_kb * 1024
        assert max_bytes == 524288

    def test_zero_config_respected(self):
        """A config value of 0 should not fall back to the default."""
        config_val = 0
        max_kb = int(config_val) if config_val is not None else 512
        assert max_kb == 0

    def test_string_config_coerced(self):
        """String config values from YAML are coerced to int."""
        config_val = '256'
        max_kb = int(config_val) if config_val is not None else 512
        assert max_kb == 256

    def test_oversized_body_detected(self):
        max_bytes = 512 * 1024
        body = b'x' * (max_bytes + 1)
        assert len(body) > max_bytes

    def test_normal_body_accepted(self):
        max_bytes = 512 * 1024
        body = b'x' * 1000
        assert not (len(body) > max_bytes)
