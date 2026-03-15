import unittest
from unittest.mock import MagicMock, patch


class TestAuthAuditLog(unittest.TestCase):
    def _make_auth_svc(self):
        from app.service.auth_svc import AuthService
        svc = AuthService.__new__(AuthService)
        svc.log = MagicMock()
        svc.user_map = {}
        svc._login_handler = None
        svc._default_login_handler = None
        return svc

    def test_log_auth_denial(self):
        svc = self._make_auth_svc()
        request = MagicMock()
        request.method = 'GET'
        request.path = '/api/v2/agents'
        request.remote = '10.0.0.1'
        request.headers = {}
        svc._log_auth_denial(request)
        svc.log.warning.assert_called_once()
        call_args = svc.log.warning.call_args[0]
        self.assertIn('AUDIT: Authorization denied', call_args[0])
        self.assertIn('GET', call_args[1])
        self.assertIn('/api/v2/agents', call_args[2])

    def test_log_invalid_api_key(self):
        svc = self._make_auth_svc()
        request = MagicMock()
        request.method = 'POST'
        request.path = '/api/v2/operations'
        request.remote = '192.168.1.1'
        request.headers = {}
        svc._log_invalid_api_key_attempt(request)
        svc.log.warning.assert_called_once()
        call_args = svc.log.warning.call_args[0]
        self.assertIn('Invalid API key', call_args[0])

    def test_get_client_ip_forwarded(self):
        from app.service.auth_svc import AuthService
        request = MagicMock()
        request.headers = {'X-Forwarded-For': '1.2.3.4, 5.6.7.8'}
        request.remote = '127.0.0.1'
        ip = AuthService._get_client_ip(request)
        self.assertEqual(ip, '1.2.3.4')


if __name__ == '__main__':
    unittest.main()
