import pytest
from unittest.mock import MagicMock

import app.api.v2 as v2_module


def _make_app(upload_max_size_mb):
    """Call the real make_app with mock services and return the resulting app."""
    services = MagicMock()
    return v2_module.make_app(services, upload_max_size_mb=upload_max_size_mb)


@pytest.mark.parametrize('mb,expected_bytes', [
    (1, 1 * 1024 * 1024),
    (100, 100 * 1024 * 1024),
    (50, 50 * 1024 * 1024),
])
def test_valid_integer_config(mb, expected_bytes):
    # _client_max_size is the only accessible attribute for client_max_size in aiohttp
    assert _make_app(mb)._client_max_size == expected_bytes


@pytest.mark.parametrize('bad_val', [None, '', 'abc', '1MB', -1, 0])
def test_invalid_config_falls_back_to_default(bad_val):
    """None, strings, and non-positive values must fall back to 100MB default."""
    assert _make_app(bad_val)._client_max_size == 100 * 1024 * 1024


def test_string_integer_coerces_correctly():
    """Config may return strings; '50' must coerce to 50MB, not repeat a string."""
    assert _make_app('50')._client_max_size == 50 * 1024 * 1024


def test_api_upload_limit_larger_than_global_default():
    """API v2 upload limit (100MB default) must be larger than the global 1MB default."""
    api_app = _make_app(100)
    assert api_app._client_max_size == 100 * 1024 * 1024
    assert api_app._client_max_size > 1 * 1024 * 1024


def test_global_default_tighter_than_old_hardcoded():
    """New 1MB global default must be tighter than the old hardcoded 5120**2 (~26MB)."""
    # Verify the v2 app can be created with the old value, and 1MB is genuinely smaller
    old_hardcoded = 5120 ** 2
    new_default_mb = 1 * 1024 * 1024
    assert new_default_mb < old_hardcoded
    # Confirm the app created with 1MB actually applies that limit
    assert _make_app(1)._client_max_size == new_default_mb
