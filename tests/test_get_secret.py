import os
import pytest
from app.utility.base_world import BaseWorld


@pytest.fixture
def setup_config():
    BaseWorld.apply_config('main', {'app.contact.gist': 'config_token', 'app.contact.slack.api_key': 'config_slack'})
    yield
    BaseWorld.clear_config()


class TestGetSecret:
    def test_env_var_takes_priority(self, setup_config):
        os.environ['CALDERA_GIST_TOKEN'] = 'env_token'
        try:
            result = BaseWorld.get_secret('app.contact.gist', env_var='CALDERA_GIST_TOKEN')
            assert result == 'env_token'
        finally:
            del os.environ['CALDERA_GIST_TOKEN']

    def test_falls_back_to_config(self, setup_config):
        result = BaseWorld.get_secret('app.contact.gist')
        assert result == 'config_token'

    def test_returns_none_when_neither(self, setup_config):
        result = BaseWorld.get_secret('nonexistent.key', env_var='NONEXISTENT_ENV_VAR')
        assert result is None

    def test_env_var_empty_string_falls_back(self, setup_config):
        os.environ['CALDERA_GIST_TOKEN'] = ''
        try:
            result = BaseWorld.get_secret('app.contact.gist', env_var='CALDERA_GIST_TOKEN')
            assert result == 'config_token'
        finally:
            del os.environ['CALDERA_GIST_TOKEN']
