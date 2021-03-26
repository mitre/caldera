import pytest
import aiohttp
import asyncssh
import time

from app.contacts.contact_ssh import Contact as SshContact
from app.utility.base_world import BaseWorld
from app.utility.file_decryptor import read as decrypt_read, get_encryptor


@pytest.fixture(scope='session')
def ssh_contact_base_world():
    BaseWorld.apply_config(name='main', config={'app.contact.ssh.user_name': 'sandcat',
                                                'app.contact.ssh.user_password': 's4ndc4t!',
                                                'app.contact.ssh.socket': '0.0.0.0:8122',
                                                'app.contact.ssh.host_key_file': 'REPLACE_WITH_KEY_FILE_PATH,',
                                                'app.contact.ssh.host_key_passphrase': 'REPLACE_WITH_KEY_FILE_PASSPHRASE',
                                                'plugins': ['sandcat', 'stockpile'],
                                                'crypt_salt': 'BLAH',
                                                'api_key': 'ADMIN123',
                                                'encryption_key': 'ADMIN123',
                                                'exfil_dir': '/tmp'})
    BaseWorld.apply_config(name='agents', config={'sleep_max': 5,
                                                  'sleep_min': 5,
                                                  'untrusted_timer': 90,
                                                  'watchdog': 0,
                                                  'implant_name': 'splunkd',
                                                  'bootstrap_abilities': [
                                                      '43b3754c-def4-4699-a673-1d85648fda6a'
                                                  ]})

@pytest.fixture
def ssh_contact(loop, app_svc, contact_svc, data_svc, file_svc, obfuscator):
    services = app_svc(loop).get_services()
    return SshContact(services)

@pytest.mark.usefixtures(
    'ssh_contact_base_world'
)
class TestContactSsh:
    @staticmethod
    async def web_request(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                print(resp.status)
                print(await resp.text())

    def test_tunnel(self, loop, ssh_contact):
        loop.run_until_complete(ssh_contact.start())
        conn = loop.run_until_complete(asyncssh.connect('localhost', port=8122, known_hosts=None, username='sandcat',
                                                        password='s4ndc4t!'))
        assert conn and conn.get_extra_info('username') == 'sandcat'
        listener = loop.run_until_complete(conn.forward_local_port('', 61234, 'localhost', 8888))
        assert listener and listener.get_port() == 61234
        listener.close()
