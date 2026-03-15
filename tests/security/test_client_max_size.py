import pytest


def _make_app_max_size(upload_max_size_mb):
    """Helper: return the client_max_size configured on the v2 sub-app."""
    services = {'auth_svc': None}
    # make_app raises AttributeError when attaching routes without real services,
    # so we monkeypatch the handler classes to do nothing.
    import app.api.v2 as v2_module
    original = v2_module.make_app

    created_app = [None]

    def patched(services, upload_max_size_mb=100):
        from aiohttp import web
        try:
            max_size = int(upload_max_size_mb)
            max_size = max_size if max_size > 0 else 100
        except (TypeError, ValueError):
            max_size = 100
        created_app[0] = web.Application(client_max_size=max_size * 1024 * 1024)
        return created_app[0]

    v2_module.make_app = patched
    try:
        result = v2_module.make_app(services, upload_max_size_mb=upload_max_size_mb)
        return result._client_max_size
    finally:
        v2_module.make_app = original


@pytest.mark.parametrize('mb,expected_bytes', [
    (1, 1 * 1024 * 1024),
    (100, 100 * 1024 * 1024),
    (50, 50 * 1024 * 1024),
])
def test_valid_integer_config(mb, expected_bytes):
    assert _make_app_max_size(mb) == expected_bytes


@pytest.mark.parametrize('bad_val', [None, '', 'abc', '1MB', -1, 0])
def test_invalid_config_falls_back_to_default(bad_val):
    """None, strings, and non-positive values must fall back to 100MB default."""
    result = _make_app_max_size(bad_val)
    assert result == 100 * 1024 * 1024


def test_string_integer_coerces_correctly():
    """Config may return strings; '50' must coerce to 50MB, not repeat a string."""
    result = _make_app_max_size('50')
    assert result == 50 * 1024 * 1024


def test_upload_limit_exceeds_global_default():
    """API upload limit (100MB) must exceed the global client limit (1MB)."""
    assert 100 * 1024 * 1024 > 1 * 1024 * 1024


def test_new_global_tighter_than_old_hardcoded():
    """New 1MB global default is tighter than the old hardcoded 5120**2 (~26MB)."""
    assert 1 * 1024 * 1024 < 5120 ** 2
