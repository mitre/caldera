import re
import unittest


def _is_valid_cors_host(host):
    return bool(re.match(r'^[a-zA-Z0-9.\-]+$', host))


class TestCorsValidation(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
