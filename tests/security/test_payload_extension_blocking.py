"""
Security regression tests for payload upload extension blocking (CWE-94 fix).

Verifies that _validate_payload_extension() correctly rejects server-side
executable file types (.py, .pyc, .pyo, .so, .dll).
"""
import pytest
from aiohttp import web

from app.api.v2.handlers.payload_api import _validate_payload_extension


class TestPayloadExtensionBlocking:

    @pytest.mark.parametrize(
        "filename",
        [
            "malicious.py",
            "malicious.pyc",
            "malicious.pyo",
            "exploit.so",
            "evil.dll",
            "malicious.PY",
            "malicious.Py",
            # Files with a safe-looking extension followed by a blocked one
            "legit.txt.py",
        ],
    )
    def test_blocked_filenames_rejected(self, filename):
        with pytest.raises(web.HTTPBadRequest):
            _validate_payload_extension(filename)

    def test_exe_allowed(self):
        """Agent binaries (.exe) must still be uploadable."""
        _validate_payload_extension('sandcat.exe')  # should not raise

    def test_elf_allowed(self):
        _validate_payload_extension('sandcat-linux')  # no extension — should not raise

    def test_zip_allowed(self):
        _validate_payload_extension('payloads.zip')

    def test_go_allowed(self):
        _validate_payload_extension('manx.go')

    def test_blocked_extensions_set(self):
        """Verify the constant is a frozenset and contains at least the known dangerous types."""
        from app.api.v2.handlers.payload_api import _BLOCKED_EXTENSIONS as _BLK
        assert isinstance(_BLK, frozenset), "_BLOCKED_EXTENSIONS must be a frozenset"
        expected_minimum = frozenset({'.py', '.pyc', '.pyo', '.so', '.dll'})
        assert _BLK.issuperset(expected_minimum), (
            f"_BLOCKED_EXTENSIONS missing required extensions: {expected_minimum - _BLK}"
        )
