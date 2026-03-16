import builtins
import copy
import pathlib
import secrets
import yaml

from unittest import mock
from argon2 import PasswordHasher

from app.utility.config_util import hash_config_creds, verify_hash, ensure_local_config, make_secure_config


NON_SENSITIVE_CONF = {
    'app.contact.http': '0.0.0.0',
    'plugins': ['sandcat', 'stockpile'],
}
SENSITIVE_CONF = {
    'app.contact.http': '0.0.0.0',
    'plugins': ['sandcat', 'stockpile'],
    'api_key_blue': 'testapikeyblue',
    'api_key_red': 'testapikeyred',
    'users': {
        'group1': {
            'user1': 'testpassword1'
        },
        'group2': {
            'user2': 'testpassword2'
        },
    }
}


class TestConfigUtil:

    def test_verify_hash(self):
        hash_val = '$argon2id$v=19$m=65536,t=3,p=4$87lgOXDGx/9JUHuCsxlaZw$bcJp3dQcqMiYdZOCm8LLJ8ncaEwjoS1xVcPHUGs/ajU'
        plaintext = 'testpassword'
        assert verify_hash(hash_val, plaintext)
        assert not verify_hash(hash_val, 'testpassword2')
        assert not verify_hash('$argon2id$v=19$m=65536,t=3,p=4$K/WRrQC6CaEkiDF+KhKfMQ$y4dB2W/sqiCcyJX3SYPYhHenEmLv4xDuKV38Ca9FrGc', plaintext)
        assert not verify_hash('notahash', plaintext)
        assert not verify_hash('$argon2id$v=19$m=65536,t=2,p=4$87lgOXDGx/9JUHuCsxlaZw$bcJp3dQcqMiYdZOCm8LLJ8ncaEwjoS1xVcPHUGs/ajU', plaintext)
        assert not verify_hash('$argon2$v=19$m=65536,t=3,p=4$87lgOXDGx/9JUHuCsxlaZw$bcJp3dQcqMiYdZOCm8LLJ8ncaEwjoS1xVcPHUGs/ajU', plaintext)
        assert not verify_hash('$argon2idasdkl$v=19$m=65536,t=2,p=4$87lgOXDGx/laksdj$bcJp3dQcqMiYdZOCm8LLJ8ncaEwjoS1xVcPHUGs/ajU', plaintext)
        assert not verify_hash(None, plaintext)
        assert not verify_hash(hash_val, None)

    def test_hash_config_creds(self):
        config = copy.deepcopy(NON_SENSITIVE_CONF)
        assert not hash_config_creds(config)
        assert config == NON_SENSITIVE_CONF

        config = copy.deepcopy(SENSITIVE_CONF)
        assert hash_config_creds(config)
        assert SENSITIVE_CONF != config
        assert verify_hash(config['api_key_blue'], 'testapikeyblue')
        assert verify_hash(config['api_key_red'], 'testapikeyred')
        assert verify_hash(config['users']['group1']['user1'], 'testpassword1')
        assert verify_hash(config['users']['group2']['user2'], 'testpassword2')

    @mock.patch.object(PasswordHasher, 'hash', return_value='mockhash')
    @mock.patch.object(yaml, 'safe_load', side_effect=lambda *a, **kw: copy.deepcopy(SENSITIVE_CONF))
    @mock.patch.object(yaml, 'safe_dump')
    @mock.patch.object(secrets, 'token_urlsafe', return_value='mocksecret')
    def test_ensure_local_config(self, mock_token_urlsafe, mock_safe_dump, mock_safe_load, mock_hashs):
        with mock.patch.object(pathlib.Path, 'open', spec=open):
            with mock.patch.object(pathlib.Path, 'exists', return_value=True):
                ensure_local_config()
                mock_safe_dump.assert_not_called()
            with mock.patch.object(pathlib.Path, 'exists', return_value=False):
                want_config = {
                    'app.contact.http': '0.0.0.0',
                    'plugins': ['sandcat', 'stockpile'],
                    'api_key_blue': 'mockhash',
                    'api_key_red': 'mockhash',
                    'crypt_salt': 'mocksecret',
                    'encryption_key': 'mocksecret',
                    'users': {
                        'red': {
                            'red': 'mockhash',
                        },
                        'blue': {
                            'blue': 'mockhash',
                        },
                    }
                }
                ensure_local_config()
                mock_safe_dump.assert_called_once_with(want_config, mock.ANY, default_flow_style=False)

    @mock.patch('logging.info')
    @mock.patch.object(yaml, 'safe_load', return_value={'app.contact.http': '0.0.0.0', 'plugins': ['sandcat']})
    @mock.patch.object(secrets, 'token_urlsafe', return_value='plaintextsecret')
    def test_make_secure_config_logs_plaintext_then_hashes(self, mock_token_urlsafe, mock_safe_load, mock_logging_info):
        with mock.patch.object(builtins, 'open', mock.mock_open()):
            config = make_secure_config()

        # logging.info must have been called exactly once (to display startup credentials)
        mock_logging_info.assert_called_once()
        logged_message = mock_logging_info.call_args[0][0]

        # The logged message must contain the plaintext secret so the admin can read their credentials
        assert 'plaintextsecret' in logged_message, (
            "Expected plaintext secret in logged startup message, got: %r" % logged_message
        )

        # The returned config must store argon2 hashes, not the plaintext secret
        assert config['api_key_blue'].startswith('$argon2id$'), (
            "api_key_blue should be an argon2 hash after make_secure_config, got: %r" % config['api_key_blue']
        )
        assert config['api_key_red'].startswith('$argon2id$'), (
            "api_key_red should be an argon2 hash after make_secure_config, got: %r" % config['api_key_red']
        )
