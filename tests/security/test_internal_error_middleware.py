import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from aiohttp import web


class TestInternalErrorMiddleware(unittest.TestCase):
    def test_generic_500_on_unhandled_exception(self):
        from app.api.v2.responses import internal_error_middleware

        request = MagicMock()
        handler = AsyncMock(side_effect=RuntimeError('secret db error'))

        loop = asyncio.new_event_loop()
        try:
            with self.assertRaises(web.HTTPInternalServerError) as ctx:
                loop.run_until_complete(internal_error_middleware(request, handler))
            self.assertIn('internal server error', ctx.exception.text)
            self.assertNotIn('secret db error', ctx.exception.text)
        finally:
            loop.close()

    def test_http_exceptions_pass_through(self):
        from app.api.v2.responses import internal_error_middleware

        request = MagicMock()
        handler = AsyncMock(side_effect=web.HTTPNotFound())

        loop = asyncio.new_event_loop()
        try:
            with self.assertRaises(web.HTTPNotFound):
                loop.run_until_complete(internal_error_middleware(request, handler))
        finally:
            loop.close()

    def test_normal_response_passes_through(self):
        from app.api.v2.responses import internal_error_middleware

        request = MagicMock()
        handler = AsyncMock(return_value=web.Response(text='ok'))

        loop = asyncio.new_event_loop()
        try:
            resp = loop.run_until_complete(internal_error_middleware(request, handler))
            self.assertEqual(resp.text, 'ok')
        finally:
            loop.close()


if __name__ == '__main__':
    unittest.main()
