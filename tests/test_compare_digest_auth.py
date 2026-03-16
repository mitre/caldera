import pytest
from unittest.mock import MagicMock, AsyncMock
from app.service.auth_svc import AuthService, HEADER_API_KEY
from app.utility.base_world import BaseWorld


@pytest.fixture(autouse=True)
def setup_config():
    BaseWorld.apply_config('main', {
        'api_key_red': 'RED_KEY_123',
        'api_key_blue': 'BLUE_KEY_456',
    })
    yield
    BaseWorld.clear_config()


class MockHeaders:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


class TestCompareDigestAuth:
    def _make_request(self, api_key=None):
        request = MagicMock()
        headers_data = {HEADER_API_KEY: api_key} if api_key else {}
        request.headers = MockHeaders(headers_data)
        identity_policy = AsyncMock()
        identity_policy.identify = AsyncMock(return_value=None)
        request.config_dict = {'aiohttp_security_identity_policy': identity_policy}
        return request

    @pytest.mark.asyncio
    async def test_red_key_returns_red_access(self):
        svc = AuthService.__new__(AuthService)
        svc.user_map = {}
        request = self._make_request('RED_KEY_123')
        result = await svc.get_permissions(request)
        assert BaseWorld.Access.RED in result
        assert BaseWorld.Access.APP in result

    @pytest.mark.asyncio
    async def test_blue_key_returns_blue_access(self):
        svc = AuthService.__new__(AuthService)
        svc.user_map = {}
        request = self._make_request('BLUE_KEY_456')
        result = await svc.get_permissions(request)
        assert BaseWorld.Access.BLUE in result
        assert BaseWorld.Access.APP in result

    @pytest.mark.asyncio
    async def test_wrong_key_returns_empty(self):
        svc = AuthService.__new__(AuthService)
        svc.user_map = {}
        request = self._make_request('WRONG_KEY')
        result = await svc.get_permissions(request)
        assert result == ()

    @pytest.mark.asyncio
    async def test_no_key_returns_empty(self):
        svc = AuthService.__new__(AuthService)
        svc.user_map = {}
        request = self._make_request(None)
        result = await svc.get_permissions(request)
        assert result == ()
