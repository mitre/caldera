import unittest
from unittest.mock import patch, MagicMock


class TestApiKeyRotation(unittest.TestCase):
    def _make_auth_svc(self):
        from app.service.auth_svc import AuthService
        svc = AuthService.__new__(AuthService)
        svc.log = MagicMock()
        svc.user_map = {}
        svc._login_handler = None
        svc._default_login_handler = None
        return svc

    def test_rotate_generates_new_key(self):
        svc = self._make_auth_svc()
        with patch.object(type(svc), 'set_config') as mock_set:
            new_key = svc.rotate_api_key('red')
        self.assertEqual(len(new_key), 64)  # hex(32 bytes) = 64 chars
        mock_set.assert_called_once()

    def test_rotate_invalid_group(self):
        svc = self._make_auth_svc()
        with self.assertRaises(ValueError):
            svc.rotate_api_key('invalid')

    def test_rotate_blue_key(self):
        svc = self._make_auth_svc()
        with patch.object(type(svc), 'set_config') as mock_set:
            new_key = svc.rotate_api_key('blue')
        self.assertEqual(len(new_key), 64)
        mock_set.assert_called_once_with('main', 'api_key_blue', new_key)


if __name__ == '__main__':
    unittest.main()
