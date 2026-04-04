import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio


class TestFilePathCache(unittest.TestCase):
    def test_cache_returns_cached_result(self):
        from app.service.file_svc import FileSvc
        svc = FileSvc.__new__(FileSvc)
        svc._path_cache = {'test.ps1:': ('sandcat', '/path/test.ps1')}
        svc.data_svc = MagicMock()
        svc.log = MagicMock()

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(svc.find_file_path('test.ps1'))
            self.assertEqual(result, ('sandcat', '/path/test.ps1'))
            # data_svc.locate should NOT have been called
            svc.data_svc.locate.assert_not_called()
        finally:
            loop.close()

    def test_invalidate_clears_cache(self):
        from app.service.file_svc import FileSvc
        svc = FileSvc.__new__(FileSvc)
        svc._path_cache = {'test.ps1:': ('sandcat', '/path/test.ps1')}
        svc.invalidate_path_cache()
        self.assertEqual(len(svc._path_cache), 0)

    def test_invalidate_specific_name(self):
        from app.service.file_svc import FileSvc
        svc = FileSvc.__new__(FileSvc)
        svc._path_cache = {'a.ps1:': ('x', '/a'), 'b.ps1:': ('y', '/b')}
        svc.invalidate_path_cache('a.ps1:')
        self.assertNotIn('a.ps1:', svc._path_cache)
        self.assertIn('b.ps1:', svc._path_cache)


if __name__ == '__main__':
    unittest.main()
