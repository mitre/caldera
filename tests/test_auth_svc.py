from tests.base_service import TestBaseServiceCase
from app.service.auth_svc import DictionaryAuthorizationPolicy
from app.service.auth_svc import AuthService


class TestDictionaryAuthorizationPolicy(TestBaseServiceCase):
    def setUp(self) -> None:
        self.user_map = {'admin': AuthService.User(username='admin', password='admin', permissions=('admin', 'user'))}
        self.dap = DictionaryAuthorizationPolicy(self.user_map)

    def test_authorized_userid(self):
        self.assertTrue(self.run_async(self.dap.authorized_userid('admin')))
        self.assertFalse(self.run_async(self.dap.authorized_userid('batman')))

    def test_permits(self):
        self.assertTrue(self.run_async(self.dap.permits('admin', 'admin')))
        self.assertFalse(self.run_async(self.dap.permits('admin', 'new_permission')))

    def test_permits_no_permission(self):
        user_map = {'user': AuthService.User(username='user', password='user', permissions=())}
        dap = DictionaryAuthorizationPolicy(user_map)
        self.assertFalse(self.run_async(dap.permits('user', 'admin')))
