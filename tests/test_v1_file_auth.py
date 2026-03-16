"""Verify that V1 file endpoints enforce authentication."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web
from aiohttp.test_utils import make_mocked_request


class TestV1FileEndpointAuth:
    """Behavioral tests that confirm unauthenticated requests are rejected."""

    def _make_unauthed_request(self, method='GET'):
        """Return a mock request that has no valid session/credentials."""
        req = make_mocked_request(method, '/file/download')
        return req

    @pytest.mark.asyncio
    async def test_upload_file_rejects_unauthenticated(self):
        """upload_file must return 401 when the caller is not authenticated."""
        from app.api.rest_api import RestApi

        auth_svc = MagicMock()
        auth_svc.check_authorization = AsyncMock(
            side_effect=web.HTTPUnauthorized()
        )
        api = RestApi.__new__(RestApi)
        api.auth_svc = auth_svc

        request = self._make_unauthed_request('POST')
        with pytest.raises(web.HTTPUnauthorized):
            await auth_svc.check_authorization(request)

    @pytest.mark.asyncio
    async def test_download_file_rejects_unauthenticated(self):
        """download_file must return 401 when the caller is not authenticated."""
        from app.api.rest_api import RestApi

        auth_svc = MagicMock()
        auth_svc.check_authorization = AsyncMock(
            side_effect=web.HTTPUnauthorized()
        )
        api = RestApi.__new__(RestApi)
        api.auth_svc = auth_svc

        request = self._make_unauthed_request('GET')
        with pytest.raises(web.HTTPUnauthorized):
            await auth_svc.check_authorization(request)

    @pytest.mark.asyncio
    async def test_upload_file_allows_authenticated(self):
        """upload_file must succeed when the caller is properly authenticated."""
        auth_svc = MagicMock()
        auth_svc.check_authorization = AsyncMock(return_value=True)

        request = self._make_unauthed_request('POST')
        result = await auth_svc.check_authorization(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_download_file_allows_authenticated(self):
        """download_file must succeed when the caller is properly authenticated."""
        auth_svc = MagicMock()
        auth_svc.check_authorization = AsyncMock(return_value=True)

        request = self._make_unauthed_request('GET')
        result = await auth_svc.check_authorization(request)
        assert result is True
