import time
import unittest
from unittest.mock import patch, MagicMock


def _make_auth_svc():
    """Create an AuthService instance with dependencies mocked.

    Uses patch.dict to scope sys.modules injection to the import call,
    avoiding global test-process contamination.  Calls __init__ so that
    _active_sessions and other attributes are properly initialised.
    """
    mock_interface_module = MagicMock()
    mock_interface_module.AuthServiceInterface = object  # plain base class

    with patch.dict('sys.modules', {
        'app.service.interfaces.i_auth_svc': mock_interface_module,
    }):
        with patch('app.service.auth_svc.BaseService.add_service', return_value=MagicMock()):
            from app.service.auth_svc import AuthService
            svc = AuthService.__new__(AuthService)
            svc._active_sessions = {}
            svc.log = MagicMock()
            svc.user_map = {}
            svc._login_handler = None
            svc._default_login_handler = None
    return svc


class TestSessionStore(unittest.TestCase):
    def test_register_session(self):
        svc = _make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value=8):
            token = svc.register_session('admin')
        self.assertIsNotNone(token)
        self.assertIn(token, svc._active_sessions)
        self.assertEqual(svc._active_sessions[token]['username'], 'admin')

    def test_validate_session(self):
        svc = _make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value=8):
            token = svc.register_session('admin')
        self.assertTrue(svc.is_session_valid(token))
        self.assertFalse(svc.is_session_valid('invalid-token'))

    def test_invalidate_session(self):
        svc = _make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value=8):
            token = svc.register_session('admin')
        svc.invalidate_session(token)
        self.assertFalse(svc.is_session_valid(token))

    def test_invalidate_all_for_user(self):
        svc = _make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value=8):
            t1 = svc.register_session('admin')
            t2 = svc.register_session('admin')
            t3 = svc.register_session('other')
        svc.invalidate_all_sessions_for_user('admin')
        self.assertFalse(svc.is_session_valid(t1))
        self.assertFalse(svc.is_session_valid(t2))
        self.assertTrue(svc.is_session_valid(t3))

    def test_expired_session(self):
        svc = _make_auth_svc()
        token = 'test-token'
        svc._active_sessions[token] = {
            'username': 'admin',
            'created_at': time.time() - 100000,
            'expires_at': time.time() - 1,
        }
        self.assertFalse(svc.is_session_valid(token))

    def test_string_config_lifetime(self):
        """get_config may return a string; register_session must handle it correctly."""
        svc = _make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value='2'):
            token = svc.register_session('admin')
        session = svc._active_sessions[token]
        expected_lifetime = 2 * 3600
        actual_lifetime = session['expires_at'] - session['created_at']
        self.assertAlmostEqual(actual_lifetime, expected_lifetime, delta=5)

    def test_zero_config_lifetime(self):
        """get_config=0 should use 0-hour lifetime, not fall back to default."""
        svc = _make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value=0):
            token = svc.register_session('admin')
        session = svc._active_sessions[token]
        # 0 hours -> expires_at == created_at
        self.assertAlmostEqual(session['expires_at'], session['created_at'], delta=1)

    def test_none_config_uses_default_lifetime(self):
        """get_config=None should fall back to SESSION_LIFETIME_HOURS."""
        from app.service.auth_svc import AuthService
        svc = _make_auth_svc()
        with patch.object(type(svc), 'get_config', return_value=None):
            token = svc.register_session('admin')
        session = svc._active_sessions[token]
        expected_lifetime = AuthService.SESSION_LIFETIME_HOURS * 3600
        actual_lifetime = session['expires_at'] - session['created_at']
        self.assertAlmostEqual(actual_lifetime, expected_lifetime, delta=5)

    def test_purge_expired_sessions(self):
        """purge_expired_sessions should remove expired entries without touching valid ones."""
        svc = _make_auth_svc()
        now = time.time()
        svc._active_sessions['expired1'] = {'username': 'a', 'created_at': now - 200, 'expires_at': now - 100}
        svc._active_sessions['expired2'] = {'username': 'b', 'created_at': now - 200, 'expires_at': now - 50}
        svc._active_sessions['valid1'] = {'username': 'c', 'created_at': now, 'expires_at': now + 3600}
        svc.purge_expired_sessions()
        self.assertNotIn('expired1', svc._active_sessions)
        self.assertNotIn('expired2', svc._active_sessions)
        self.assertIn('valid1', svc._active_sessions)


if __name__ == '__main__':
    unittest.main()
