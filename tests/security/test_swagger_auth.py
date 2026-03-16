import pytest
from unittest.mock import AsyncMock, MagicMock
from aiohttp import web

from app.api.v2.security import docs_guard_middleware_factory


class TestSwaggerDocsAuth:
    """Tests for the docs_guard_middleware that protects /api/docs and /static/swagger."""

    def _make_middleware(self, *, api_key_valid=False, session_valid=False):
        auth_svc = MagicMock()
        auth_svc.request_has_valid_api_key.return_value = api_key_valid
        auth_svc.request_has_valid_user_session = AsyncMock(return_value=session_valid)
        return docs_guard_middleware_factory(auth_svc)

    @pytest.mark.asyncio
    async def test_docs_guard_blocks_unauthenticated(self):
        """Test that /api/docs paths are blocked without auth."""
        middleware = self._make_middleware()
        request = MagicMock()
        request.path = '/api/docs'
        handler = AsyncMock()

        with pytest.raises(web.HTTPUnauthorized):
            await middleware(request, handler)

    @pytest.mark.asyncio
    async def test_docs_guard_allows_api_key(self):
        """Test that /api/docs paths are allowed with valid API key."""
        middleware = self._make_middleware(api_key_valid=True)
        request = MagicMock()
        request.path = '/api/docs'
        handler = AsyncMock(return_value='ok')

        result = await middleware(request, handler)
        assert result == 'ok'

    @pytest.mark.asyncio
    async def test_docs_guard_ignores_other_paths(self):
        """Test that non-docs paths pass through without auth check."""
        middleware = self._make_middleware()
        request = MagicMock()
        request.path = '/api/v2/agents'
        handler = AsyncMock(return_value='ok')

        result = await middleware(request, handler)
        assert result == 'ok'

    @pytest.mark.asyncio
    async def test_docs_guard_allows_valid_user_session(self):
        """API key invalid but valid user session should allow /api/docs access."""
        middleware = self._make_middleware(session_valid=True)
        request = MagicMock()
        request.path = '/api/docs'
        handler = AsyncMock(return_value='ok')

        result = await middleware(request, handler)
        assert result == 'ok'

    @pytest.mark.asyncio
    async def test_docs_guard_allows_static_swagger_with_session(self):
        """Valid user session should also permit access to /static/swagger paths."""
        middleware = self._make_middleware(session_valid=True)
        request = MagicMock()
        request.path = '/static/swagger/ui.js'
        handler = AsyncMock(return_value='script')

        result = await middleware(request, handler)
        assert result == 'script'
