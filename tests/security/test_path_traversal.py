"""
Security regression tests for path traversal via API id fields.

Verifies that _sanitize_id() in BaseApiManager correctly rejects
traversal sequences like '../', absolute paths, and empty ids.
"""
import pytest

from app.api.v2.managers.base_api_manager import BaseApiManager


class TestSanitizeId:

    def test_normal_id_passes(self):
        assert BaseApiManager._sanitize_id('abc123') == 'abc123'

    def test_uuid_passes(self):
        assert BaseApiManager._sanitize_id('f489321f-31b6-ef36-3042-94562d3d4645') == 'f489321f-31b6-ef36-3042-94562d3d4645'

    def test_traversal_rejected(self):
        # IDs containing traversal sequences must be rejected outright, not silently rewritten.
        # Silently rewriting '../../etc/passwd' -> 'passwd' would cause ID collisions.
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('../../etc/passwd')

    def test_absolute_path_rejected(self):
        # Absolute paths must be rejected rather than silently stripped to their basename.
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('/etc/passwd')

    def test_leading_dot_rejected(self):
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('.hidden')

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('')

    def test_traversal_to_dotdot_raises(self):
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('../..')

    def test_traversal_to_dot_raises(self):
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('../../.')

    def test_traversal_with_url_encoding_rejected(self):
        # URL-encoded separators should be rejected; '..%2F' contains '..'
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('..%2Fetc%2Fpasswd')

    def test_windows_backslash_rejected(self):
        # Backslash traversal sequences contain '..' and are rejected
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('..\\..\\windows\\system32')

    def test_trailing_slash_raises(self):
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('someid/')

    def test_root_slash_raises(self):
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('/')

    def test_alphanumeric_with_hyphens_passes(self):
        val = 'my-objective-2024'
        assert BaseApiManager._sanitize_id(val) == val

    def test_id_with_underscores_passes(self):
        val = 'some_object_id_42'
        assert BaseApiManager._sanitize_id(val) == val

    def test_embedded_dotdot_in_id_passes(self):
        # Embedded '..' without a path separator is not a traversal sequence and is permitted.
        # e.g. 'version..2' is a valid slug-style ID; it cannot escape the directory
        # because no path separator is present.
        val = 'version..2'
        assert BaseApiManager._sanitize_id(val) == val

    def test_standalone_dotdot_raises(self):
        # '..' alone IS a traversal token and must be rejected.
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('..')
