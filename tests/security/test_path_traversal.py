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

    def test_traversal_stripped(self):
        # os.path.basename('../../etc/passwd') == 'passwd'
        result = BaseApiManager._sanitize_id('../../etc/passwd')
        assert result == 'passwd'
        assert '..' not in result
        assert '/' not in result

    def test_absolute_path_stripped(self):
        # os.path.basename('/etc/passwd') == 'passwd'
        result = BaseApiManager._sanitize_id('/etc/passwd')
        assert result == 'passwd'

    def test_leading_dot_rejected(self):
        # os.path.basename('.hidden') == '.hidden', which starts with '.' -> ValueError
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('.hidden')

    def test_empty_id_rejected(self):
        # os.path.basename('') == '' -> ValueError
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('')

    def test_traversal_to_empty_raises(self):
        # os.path.basename('../..') == '..' which starts with '.' -> ValueError
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('../..')

    def test_traversal_to_dot_raises(self):
        # os.path.basename('../../.') == '.' which starts with '.' -> ValueError
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('../../.')

    def test_traversal_with_url_encoding_rejected(self):
        # os.path.basename('..%2Fetc%2Fpasswd') returns '..%2Fetc%2Fpasswd' unchanged
        # (no real '/' chars, so basename can't strip anything). The result starts with '.'
        # so ValueError is raised — the id is safely rejected.
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('..%2Fetc%2Fpasswd')

    def test_windows_backslash_rejected(self):
        # On Linux backslashes are not path separators; os.path.basename returns the full
        # string unchanged. It starts with '.' so ValueError is raised.
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('..\\..\\windows\\system32')

    def test_trailing_slash_raises(self):
        # os.path.basename('someid/') == '' -> ValueError
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('someid/')

    def test_root_slash_raises(self):
        # os.path.basename('/') == '' -> ValueError
        with pytest.raises(ValueError):
            BaseApiManager._sanitize_id('/')

    def test_alphanumeric_with_hyphens_passes(self):
        val = 'my-objective-2024'
        assert BaseApiManager._sanitize_id(val) == val

    def test_id_with_underscores_passes(self):
        val = 'some_object_id_42'
        assert BaseApiManager._sanitize_id(val) == val
