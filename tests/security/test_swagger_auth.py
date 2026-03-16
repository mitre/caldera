import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


class TestSwaggerDocsAuth(unittest.TestCase):
    def test_docs_guard_blocks_unauthenticated(self):
        """Test that /api/docs paths are blocked without auth."""
        from app.api.v2.security import docs_guard_middleware_factory
        from aiohttp import web

        auth_svc = MagicMock()
        auth_svc.request_has_valid_api_key.return_value = False
        auth_svc.request_has_valid_user_session = AsyncMock(return_value=False)

        middleware = docs_guard_middleware_factory(auth_svc)

        request = MagicMock()
        request.path = '/api/docs'
        handler = AsyncMock()

        loop = asyncio.new_event_loop()
        try:
            with self.assertRaises(web.HTTPUnauthorized):
                loop.run_until_complete(middleware(request, handler))
        finally:
            loop.close()

    def test_docs_guard_allows_authenticated(self):
        """Test that /api/docs paths are allowed with valid API key."""
        from app.api.v2.security import docs_guard_middleware_factory

        auth_svc = MagicMock()
        auth_svc.request_has_valid_api_key.return_value = True

        middleware = docs_guard_middleware_factory(auth_svc)

        request = MagicMock()
        request.path = '/api/docs'
        handler = AsyncMock(return_value='ok')

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(middleware(request, handler))
            self.assertEqual(result, 'ok')
        finally:
            loop.close()

    def test_docs_guard_ignores_other_paths(self):
        """Test that non-docs paths are not affected."""
        from app.api.v2.security import docs_guard_middleware_factory

        auth_svc = MagicMock()
        auth_svc.request_has_valid_api_key.return_value = False

        middleware = docs_guard_middleware_factory(auth_svc)

        request = MagicMock()
        request.path = '/api/v2/agents'
        handler = AsyncMock(return_value='ok')

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(middleware(request, handler))
            self.assertEqual(result, 'ok')
        finally:
            loop.close()

    def test_docs_guard_allows_valid_user_session(self):
        """API key invalid but valid user session should allow access to /api/docs."""
        from app.api.v2.security import docs_guard_middleware_factory

        auth_svc = MagicMock()
        auth_svc.request_has_valid_api_key.return_value = False
        auth_svc.request_has_valid_user_session = AsyncMock(return_value=True)

        middleware = docs_guard_middleware_factory(auth_svc)

        request = MagicMock()
        request.path = '/api/docs'
        handler = AsyncMock(return_value='ok')

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(middleware(request, handler))
            self.assertEqual(result, 'ok')
        finally:
            loop.close()

    def test_docs_guard_allows_static_swagger_with_session(self):
        """Valid user session should also permit access to /static/swagger paths."""
        from app.api.v2.security import docs_guard_middleware_factory

        auth_svc = MagicMock()
        auth_svc.request_has_valid_api_key.return_value = False
        auth_svc.request_has_valid_user_session = AsyncMock(return_value=True)

        middleware = docs_guard_middleware_factory(auth_svc)

        request = MagicMock()
        request.path = '/static/swagger/ui.js'
        handler = AsyncMock(return_value='script')

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(middleware(request, handler))
            self.assertEqual(result, 'script')
        finally:
            loop.close()


if __name__ == '__main__':
    unittest.main()
