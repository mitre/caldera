"""
Security regression tests for v1 REST API config disclosure fix.

Verifies that _SENSITIVE_PROPS are:
  1. Stripped from update_config() response regardless of what was requested
  2. Cannot be overwritten via update_config() (set_config is not called)
  3. Normal (non-sensitive) props remain readable and writable
"""
import pytest
from unittest.mock import patch, MagicMock

from app.service.rest_svc import RestService, _SENSITIVE_PROPS
from app.utility.base_world import BaseWorld


FULL_CONFIG = {
    'port': 8888,
    'api_key_red': 'REDSECRET',
    'api_key_blue': 'BLUESECRET',
    'encryption_key': 'ENCKEY',
    'crypt_salt': 'SALT',
    'users': {'admin': 'pass'},
    'auth.login.handler.module': 'default',
    'auth.login.handler.options': {},
    'plugins': ['stockpile'],
    'app.contact.http': '0.0.0.0',
}


@pytest.fixture
async def rest_svc():
    return RestService()


@pytest.fixture(autouse=True)
def apply_full_config():
    """Load a complete config that includes all sensitive keys before each test."""
    BaseWorld.apply_config('main', dict(FULL_CONFIG), apply_hash=False)
    yield


class TestSensitivePropsNotInResponse:

    async def test_normal_update_strips_all_sensitive_keys(self, rest_svc):
        """update_config() response must never include any sensitive key."""
        result = await rest_svc.update_config({'prop': 'port', 'value': 9999})
        for key in _SENSITIVE_PROPS:
            assert key not in result, f"Sensitive key {key!r} leaked in response"

    async def test_sensitive_prop_request_response_still_stripped(self, rest_svc):
        """Even when requesting a sensitive prop, response must not include sensitive keys."""
        result = await rest_svc.update_config({'prop': 'api_key_red', 'value': 'EVIL'})
        for key in _SENSITIVE_PROPS:
            assert key not in result, f"Sensitive key {key!r} leaked in response"

    async def test_non_sensitive_key_present_in_response(self, rest_svc):
        """Non-sensitive keys (e.g. port) must still appear in the response."""
        result = await rest_svc.update_config({'prop': 'port', 'value': 9999})
        assert 'port' in result, "Non-sensitive key 'port' should be in response"


class TestSensitivePropsWriteBlocked:

    async def test_api_key_red_write_blocked(self, rest_svc):
        """Writing api_key_red must not call set_config."""
        with patch.object(BaseWorld, 'set_config') as mock_set:
            await rest_svc.update_config({'prop': 'api_key_red', 'value': 'EVIL'})
        mock_set.assert_not_called()

    async def test_api_key_blue_write_blocked(self, rest_svc):
        """Writing api_key_blue must not call set_config."""
        with patch.object(BaseWorld, 'set_config') as mock_set:
            await rest_svc.update_config({'prop': 'api_key_blue', 'value': 'EVIL'})
        mock_set.assert_not_called()

    async def test_encryption_key_write_blocked(self, rest_svc):
        """Writing encryption_key must not call set_config."""
        with patch.object(BaseWorld, 'set_config') as mock_set:
            await rest_svc.update_config({'prop': 'encryption_key', 'value': 'EVIL'})
        mock_set.assert_not_called()

    async def test_crypt_salt_write_blocked(self, rest_svc):
        """Writing crypt_salt must not call set_config."""
        with patch.object(BaseWorld, 'set_config') as mock_set:
            await rest_svc.update_config({'prop': 'crypt_salt', 'value': 'EVIL'})
        mock_set.assert_not_called()

    async def test_users_write_blocked(self, rest_svc):
        """Writing users must not call set_config."""
        with patch.object(BaseWorld, 'set_config') as mock_set:
            await rest_svc.update_config({'prop': 'users', 'value': {'evil': 'evil'}})
        mock_set.assert_not_called()

    async def test_login_handler_module_write_blocked(self, rest_svc):
        """auth.login.handler.module must be immutable via v1 API."""
        with patch.object(BaseWorld, 'set_config') as mock_set:
            await rest_svc.update_config({'prop': 'auth.login.handler.module', 'value': 'evil.module'})
        mock_set.assert_not_called()

    async def test_login_handler_options_write_blocked(self, rest_svc):
        """auth.login.handler.options must be immutable via v1 API."""
        with patch.object(BaseWorld, 'set_config') as mock_set:
            await rest_svc.update_config({'prop': 'auth.login.handler.options', 'value': {'evil': True}})
        mock_set.assert_not_called()

    async def test_all_sensitive_props_covered(self, rest_svc):
        """Every member of _SENSITIVE_PROPS must be blocked from writing."""
        for prop in _SENSITIVE_PROPS:
            with patch.object(BaseWorld, 'set_config') as mock_set:
                await rest_svc.update_config({'prop': prop, 'value': 'EVIL'})
            assert not mock_set.called, (
                f"set_config was called when writing sensitive prop {prop!r}"
            )


class TestNonSensitivePropsStillWritable:

    async def test_port_is_writable(self, rest_svc):
        """Normal prop 'port' must still be updatable via v1 API."""
        with patch.object(BaseWorld, 'set_config') as mock_set:
            await rest_svc.update_config({'prop': 'port', 'value': 9999})
        mock_set.assert_called_once_with('main', 'port', 9999)

    async def test_app_contact_http_is_writable(self, rest_svc):
        """Normal prop 'app.contact.http' must still be updatable via v1 API."""
        with patch.object(BaseWorld, 'set_config') as mock_set:
            await rest_svc.update_config({'prop': 'app.contact.http', 'value': '127.0.0.1'})
        mock_set.assert_called_once_with('main', 'app.contact.http', '127.0.0.1')
