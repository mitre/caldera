import unittest
from server import _is_valid_cors_host


class TestCorsValidation(unittest.TestCase):
    """Tests for the CORS host validation helper in server.py.

    Imports _is_valid_cors_host directly so tests always exercise the
    production implementation rather than a duplicate local copy.
    """

    def test_valid_hostname(self):
        self.assertTrue(_is_valid_cors_host('localhost'))
        self.assertTrue(_is_valid_cors_host('my-host.local'))
        self.assertTrue(_is_valid_cors_host('192.168.1.1'))

    def test_invalid_hostname_with_special_chars(self):
        self.assertFalse(_is_valid_cors_host('host;rm -rf /'))
        self.assertFalse(_is_valid_cors_host('host<script>'))
        self.assertFalse(_is_valid_cors_host(''))
        self.assertFalse(_is_valid_cors_host('host name'))
        self.assertFalse(_is_valid_cors_host('host\x00name'))

    def test_none_is_invalid(self):
        self.assertFalse(_is_valid_cors_host(None))

    def test_fullmatch_not_partial(self):
        """Ensure partial matches are rejected (e.g. valid prefix + injection suffix)."""
        self.assertFalse(_is_valid_cors_host('localhost;evil'))
        self.assertFalse(_is_valid_cors_host('localhost evil'))
