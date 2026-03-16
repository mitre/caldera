"""
Security regression tests for payload upload extension blocking (CWE-94 fix).

Verifies that _validate_payload_extension() correctly rejects server-side
executable file types (.py, .pyc, .pyo, .so, .dll).
"""
import pytest
from aiohttp import web

from app.api.v2.handlers.payload_api import _validate_payload_extension, _BLOCKED_EXTENSIONS


class TestPayloadExtensionBlocking:

    def test_py_file_rejected(self):
        with pytest.raises(web.HTTPBadRequest):
            _validate_payload_extension('malicious.py')

    def test_pyc_file_rejected(self):
        with pytest.raises(web.HTTPBadRequest):
            _validate_payload_extension('malicious.pyc')

    def test_pyo_file_rejected(self):
        with pytest.raises(web.HTTPBadRequest):
            _validate_payload_extension('malicious.pyo')

    def test_so_file_rejected(self):
        with pytest.raises(web.HTTPBadRequest):
            _validate_payload_extension('exploit.so')

    def test_dll_file_rejected(self):
        with pytest.raises(web.HTTPBadRequest):
            _validate_payload_extension('evil.dll')

    def test_uppercase_extension_rejected(self):
        with pytest.raises(web.HTTPBadRequest):
            _validate_payload_extension('malicious.PY')

    def test_mixed_case_extension_rejected(self):
        with pytest.raises(web.HTTPBadRequest):
            _validate_payload_extension('malicious.Py')

    def test_exe_allowed(self):
        """Agent binaries (.exe) must still be uploadable."""
        _validate_payload_extension('sandcat.exe')  # should not raise

    def test_elf_allowed(self):
        _validate_payload_extension('sandcat-linux')  # no extension — should not raise

    def test_zip_allowed(self):
        _validate_payload_extension('payloads.zip')

    def test_go_allowed(self):
        _validate_payload_extension('manx.go')

    def test_double_extension_py_blocked(self):
        """Files like 'legit.txt.py' must still be rejected."""
        with pytest.raises(web.HTTPBadRequest):
            _validate_payload_extension('legit.txt.py')

    def test_blocked_extensions_set(self):
        """Verify the constant is a frozenset and contains exactly the expected types."""
        from app.api.v2.handlers.payload_api import _BLOCKED_EXTENSIONS as _BLK
        assert isinstance(_BLK, frozenset), "_BLOCKED_EXTENSIONS must be a frozenset"
        expected = frozenset({'.py', '.pyc', '.pyo', '.so', '.dll'})
        assert _BLK == expected, (
            f"_BLOCKED_EXTENSIONS mismatch: got {_BLK}, expected {expected}"
        )
