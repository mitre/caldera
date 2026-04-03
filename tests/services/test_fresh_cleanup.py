"""Tests proving that --fresh cleanup and auth_svc recovery work correctly.

These tests verify:
1. data/cookie_storage is cleaned by --fresh (via DATA_FILE_GLOBS)
2. auth_svc recovers gracefully when cookie_storage was encrypted with a different key
"""
import os

import pytest

from aiohttp import web
from app.service.auth_svc import AuthService, CONFIG_API_KEY_RED
from app.service.data_svc import DATA_FILE_GLOBS
from app.service.file_svc import FileSvc
from app.utility.base_world import BaseWorld

class TestDataFileGlobs:
    """Verify that critical encrypted files are included in the --fresh cleanup list."""

    def test_cookie_storage_in_data_file_globs(self):
        assert any('cookie_storage' in pattern for pattern in DATA_FILE_GLOBS), \
            'data/cookie_storage must be in DATA_FILE_GLOBS so --fresh cleans it up'

    def test_object_store_in_data_file_globs(self):
        assert any('object_store' in pattern for pattern in DATA_FILE_GLOBS), \
            'data/object_store must be in DATA_FILE_GLOBS'


class TestAuthSvcCookieRecovery:
    """Verify auth_svc recovers when cookie_storage has a stale encryption key."""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        self.cookie_path = os.path.join('data', 'cookie_storage')
        if os.path.exists(self.cookie_path):
            os.remove(self.cookie_path)
        yield
        if os.path.exists(self.cookie_path):
            os.remove(self.cookie_path)
        BaseWorld.clear_config()

    def _apply_config(self, encryption_key):
        BaseWorld.clear_config()
        BaseWorld.apply_config(
            name='main',
            config={
                CONFIG_API_KEY_RED: 'abc123',
                'crypt_salt': 'REPLACE_WITH_RANDOM_VALUE',
                'encryption_key': encryption_key,
                'users': {
                    'red': {'reduser': 'redpass'},
                    'blue': {'blueuser': 'bluepass'}
                },
            },
            apply_hash=True
        )
        # Ensure file_svc is registered so auth_svc can use it
        FileSvc()

    @pytest.mark.asyncio
    async def test_stale_cookie_does_not_crash_server(self):
        """Prove that a cookie_storage encrypted with key A doesn't crash when loaded with key B."""
        # Step 1: Create cookie_storage with encryption key A
        self._apply_config('KEY_ALPHA_123')
        app1 = web.Application()
        auth1 = AuthService()
        await auth1.apply(app=app1, users=BaseWorld.get_config('users'))
        assert os.path.exists(self.cookie_path), 'cookie_storage should be created'

        # Step 2: Switch to encryption key B and re-init auth
        # Before fix: this would sys.exit(1) due to InvalidToken in file_svc._read()
        # After fix: auth_svc catches the error, regenerates the key, and continues
        self._apply_config('KEY_BETA_456')
        app2 = web.Application()
        auth2 = AuthService()
        # This should NOT crash
        await auth2.apply(app=app2, users=BaseWorld.get_config('users'))
        # cookie_storage should still exist (regenerated with new key)
        assert os.path.exists(self.cookie_path), 'cookie_storage should be regenerated'
