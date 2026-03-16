import unittest
from unittest.mock import MagicMock


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

    def test_log_auth_denial_with_reason(self):
        """When reason is provided it must appear in the log message without trailing spaces."""
        svc = self._make_auth_svc()
        request = MagicMock()
        request.method = 'DELETE'
        request.path = '/api/v2/agents/abc'
        request.remote = '10.0.0.2'
        request.headers = {}
        svc._log_auth_denial(request, reason='missing-permission')
        svc.log.warning.assert_called_once()
        call_args = svc.log.warning.call_args[0]
        # The format string should embed 'reason=' when a reason is given.
        self.assertIn('reason=', call_args[0])
        self.assertEqual(call_args[-1], 'missing-permission')

    def test_log_auth_denial_no_trailing_space(self):
        """When reason is empty the log format string must not end with a trailing space."""
        svc = self._make_auth_svc()
        request = MagicMock()
        request.method = 'GET'
        request.path = '/api/v2/facts'
        request.remote = '10.0.0.3'
        request.headers = {}
        svc._log_auth_denial(request)
        call_args = svc.log.warning.call_args[0]
        # Format string itself should not trail with a bare ' %s' placeholder.
        self.assertFalse(call_args[0].endswith(' %s'),
                         "Log format string must not end with a dangling ' %s' when reason is empty")

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

    def test_get_client_ip_no_forward(self):
        """Without X-Forwarded-For, remote address should be used."""
        from app.service.auth_svc import AuthService
        request = MagicMock()
        request.headers = {}
        request.remote = '172.16.0.5'
        ip = AuthService._get_client_ip(request)
        self.assertEqual(ip, '172.16.0.5')
