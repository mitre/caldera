import unittest

from app.api.v2.handlers.payload_api import _validate_payload_file


class TestPayloadValidation(unittest.TestCase):
    def test_valid_extension(self):
        ok, _ = _validate_payload_file('test.ps1', b'\x00\x00\x00\x00')
        self.assertTrue(ok)

    def test_invalid_extension(self):
        ok, msg = _validate_payload_file('test.php', b'normal content')
        self.assertFalse(ok)
        self.assertIn('extension', msg.lower())

    def test_dangerous_magic_bytes_php(self):
        ok, msg = _validate_payload_file('test.txt', b'<?php echo "hi";')
        self.assertFalse(ok)
        self.assertIn('Dangerous', msg)

    def test_dangerous_magic_bytes_jsp(self):
        ok, msg = _validate_payload_file('test.txt', b'<%@ page import')
        self.assertFalse(ok)

    def test_null_byte_in_filename(self):
        ok, msg = _validate_payload_file('test\x00.txt', b'safe')
        self.assertFalse(ok)
        self.assertIn('Null byte', msg)

    def test_no_extension_is_allowed(self):
        ok, _ = _validate_payload_file('myagent', b'\x7fELF')
        self.assertTrue(ok)

    def test_redundant_asp_page_signature_still_blocked(self):
        """b'<%@ Page' must still be rejected because b'<%@' prefix matches it."""
        ok, _ = _validate_payload_file('test.txt', b'<%@ Page Language')
        self.assertFalse(ok)
