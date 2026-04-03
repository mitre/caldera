"""Tests for --fresh cleanup and auth_svc cookie recovery."""
import copy
import os

import pytest

from app.service.auth_svc import AuthService, CONFIG_API_KEY_RED
from app.service.data_svc import DATA_FILE_GLOBS
from app.service.file_svc import FileSvc
from app.utility.base_world import BaseWorld


class TestDataFileGlobs:
    """Verify that critical encrypted files are in the --fresh cleanup list."""

    def test_cookie_storage_in_data_file_globs(self):
        assert any('cookie_storage' in p for p in DATA_FILE_GLOBS), \
            'data/cookie_storage must be in DATA_FILE_GLOBS so --fresh cleans it up'

    def test_object_store_in_data_file_globs(self):
        assert any('object_store' in p for p in DATA_FILE_GLOBS), \
            'data/object_store must be in DATA_FILE_GLOBS'


class TestAuthSvcCookieRecovery:
    """Verify auth_svc recovers when cookie_storage has a stale encryption key."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        self.cookie_path = os.path.join('data', 'cookie_storage')
        # Save existing state
        self._saved_config = copy.deepcopy(BaseWorld._app_configuration)
        # Clean pre-existing cookie
        if os.path.exists(self.cookie_path):
            os.remove(self.cookie_path)
        yield
        # Restore original state — leave no trace
        if os.path.exists(self.cookie_path):
            os.remove(self.cookie_path)
        BaseWorld._app_configuration = self._saved_config

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
        FileSvc()

    @pytest.mark.asyncio
    async def test_stale_cookie_does_not_crash_server(self):
        """Cookie encrypted with key A must not crash server when loaded with key B."""
        from aiohttp import web

        # Round 1: create cookie_storage with key A
        self._apply_config('KEY_ALPHA_123')
        auth1 = AuthService()
        await auth1.apply(app=web.Application(), users=BaseWorld.get_config('users'))
        assert os.path.exists(self.cookie_path), 'cookie_storage should be created'

        # Round 2: switch to key B — before fix this was sys.exit(1)
        self._apply_config('KEY_BETA_456')
        auth2 = AuthService()
        await auth2.apply(app=web.Application(), users=BaseWorld.get_config('users'))
        assert os.path.exists(self.cookie_path), 'cookie_storage should be regenerated'
