import time
import unittest
from unittest.mock import patch, MagicMock

# We need to mock the services before import
import sys
sys.modules.setdefault('app.service.interfaces.i_auth_svc', MagicMock())


class TestSessionStore(unittest.TestCase):
    def _make_auth_svc(self):
        from app.service.auth_svc import AuthService
        with patch.object(AuthService, 'add_service', return_value=MagicMock()):
            svc = AuthService.__new__(AuthService)
            svc._active_sessions = {}
            svc.log = MagicMock()
            svc.user_map = {}
            svc._login_handler = None
            svc._default_login_handler = None
        return svc

    def test_register_session(self):
        svc = self._make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value=8):
            token = svc.register_session('admin')
        self.assertIsNotNone(token)
        self.assertIn(token, svc._active_sessions)
        self.assertEqual(svc._active_sessions[token]['username'], 'admin')

    def test_validate_session(self):
        svc = self._make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value=8):
            token = svc.register_session('admin')
        self.assertTrue(svc.is_session_valid(token))
        self.assertFalse(svc.is_session_valid('invalid-token'))

    def test_invalidate_session(self):
        svc = self._make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value=8):
            token = svc.register_session('admin')
        svc.invalidate_session(token)
        self.assertFalse(svc.is_session_valid(token))

    def test_invalidate_all_for_user(self):
        svc = self._make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value=8):
            t1 = svc.register_session('admin')
            t2 = svc.register_session('admin')
            t3 = svc.register_session('other')
        svc.invalidate_all_sessions_for_user('admin')
        self.assertFalse(svc.is_session_valid(t1))
        self.assertFalse(svc.is_session_valid(t2))
        self.assertTrue(svc.is_session_valid(t3))

    def test_expired_session(self):
        svc = self._make_auth_svc()
        token = 'test-token'
        svc._active_sessions[token] = {
            'username': 'admin',
            'created_at': time.time() - 100000,
            'expires_at': time.time() - 1,
        }
        self.assertFalse(svc.is_session_valid(token))


if __name__ == '__main__':
    unittest.main()
