import copy
import pathlib
import secrets
import yaml

from unittest import mock
from argon2 import PasswordHasher

from app.utility.config_util import hash_config_creds, verify_hash, ensure_local_config


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
        hash = '$argon2id$v=19$m=65536,t=3,p=4$87lgOXDGx/9JUHuCsxlaZw$bcJp3dQcqMiYdZOCm8LLJ8ncaEwjoS1xVcPHUGs/ajU'
        plaintext = 'testpassword'
        assert verify_hash(hash, plaintext)
        assert not verify_hash(hash, 'testpassword2')
        assert not verify_hash('$argon2id$v=19$m=65536,t=3,p=4$K/WRrQC6CaEkiDF+KhKfMQ$y4dB2W/sqiCcyJX3SYPYhHenEmLv4xDuKV38Ca9FrGc', plaintext)
        assert not verify_hash('notahash', plaintext)
        assert not verify_hash('$argon2id$v=19$m=65536,t=2,p=4$87lgOXDGx/9JUHuCsxlaZw$bcJp3dQcqMiYdZOCm8LLJ8ncaEwjoS1xVcPHUGs/ajU', plaintext)
        assert not verify_hash('$argon2$v=19$m=65536,t=3,p=4$87lgOXDGx/9JUHuCsxlaZw$bcJp3dQcqMiYdZOCm8LLJ8ncaEwjoS1xVcPHUGs/ajU', plaintext)
        assert not verify_hash('$argon2idasdkl$v=19$m=65536,t=2,p=4$87lgOXDGx/laksdj$bcJp3dQcqMiYdZOCm8LLJ8ncaEwjoS1xVcPHUGs/ajU', plaintext)

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
    @mock.patch.object(yaml, 'safe_load', return_value=SENSITIVE_CONF)
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
