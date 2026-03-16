import os
import pytest

from cryptography.fernet import Fernet

from app.service.auth_svc import AuthService


@pytest.fixture
def key_path(tmp_path):
    """Return a temporary path for the cookie key file."""
    return str(tmp_path / 'cookie_key')


@pytest.fixture(autouse=True)
def _patch_key_path(monkeypatch, key_path):
    """Redirect _get_or_create_cookie_key to use a temp directory.

    Patches only the COOKIE_KEY_PATH constant rather than os.path.join,
    which would be too broad and could affect other code paths in auth_svc.
    """
    monkeypatch.setattr(
        'app.service.auth_svc.COOKIE_KEY_PATH',
        key_path,
    )


class TestCookieKeyPersistence:
    """Verify that the Fernet cookie key is persisted to disk."""

    def test_key_file_created_on_first_call(self, key_path):
        """A new key file should be created when none exists."""
        assert not os.path.exists(key_path)
        AuthService._get_or_create_cookie_key()
        assert os.path.exists(key_path)

    def test_key_is_valid_fernet_key(self, key_path):
        """The persisted key must be a valid Fernet key."""
        key = AuthService._get_or_create_cookie_key()
        # This will raise if the key is invalid
        Fernet(key)

    def test_same_key_returned_on_subsequent_calls(self, key_path):
        """Subsequent calls must return the same key (simulating restart)."""
        first_key = AuthService._get_or_create_cookie_key()
        second_key = AuthService._get_or_create_cookie_key()
        assert first_key == second_key

    def test_key_file_permissions(self, key_path):
        """The key file should have 0600 permissions."""
        AuthService._get_or_create_cookie_key()
        mode = os.stat(key_path).st_mode & 0o777
        assert mode == 0o600, f'Expected 0600, got {oct(mode)}'

    def test_session_survives_restart(self, key_path):
        """With the same key, encrypted cookies remain decryptable after restart."""
        key = AuthService._get_or_create_cookie_key()
        f = Fernet(key)
        token = f.encrypt(b'session-data')

        # Simulate restart: load key again and decrypt
        key_after_restart = AuthService._get_or_create_cookie_key()
        f2 = Fernet(key_after_restart)
        assert f2.decrypt(token) == b'session-data'
