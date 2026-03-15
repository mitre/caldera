import pytest
from unittest.mock import MagicMock, AsyncMock
from aiohttp import web
from app.api.v2.security import pass_option_middleware


class TestOptionsAuthMiddleware:
    def test_options_non_api_returns_ok(self):
        """OPTIONS on non-API paths should auto-return 200."""
        import asyncio
        request = MagicMock()
        request.method = 'OPTIONS'
        request.path = '/some/ui/path'
        handler = AsyncMock(return_value=web.Response(status=200))

        with pytest.raises(web.HTTPOk):
            asyncio.run(pass_option_middleware(request, handler))

    def test_options_api_v2_passes_through(self):
        """OPTIONS on /api/v2/ paths should NOT auto-return 200."""
        import asyncio
        request = MagicMock()
        request.method = 'OPTIONS'
        request.path = '/api/v2/agents'
        handler = AsyncMock(return_value=web.Response(status=200))

        result = asyncio.run(pass_option_middleware(request, handler))
        handler.assert_called_once_with(request)

    def test_get_request_passes_through(self):
        """Non-OPTIONS requests always pass through."""
        import asyncio
        request = MagicMock()
        request.method = 'GET'
        request.path = '/any/path'
        handler = AsyncMock(return_value=web.Response(status=200))

        result = asyncio.run(pass_option_middleware(request, handler))
        handler.assert_called_once_with(request)
