import pytest
import aiohttp
import asyncssh

from app.contacts.tunnels.tunnel_ssh import Tunnel as SshTunnel
from app.utility.base_world import BaseWorld


@pytest.fixture(scope='session')
def ssh_contact_base_world():
    BaseWorld.apply_config(name='main', config={'app.contact.tunnel.ssh.user_name': 'sandcat',
                                                'app.contact.tunnel.ssh.user_password': 's4ndc4t!',
                                                'app.contact.tunnel.ssh.socket': '0.0.0.0:8122',
                                                'app.contact.tunnel.ssh.host_key_file': 'REPLACE_WITH_KEY_FILE_PATH,',
                                                'app.contact.tunnel.ssh.host_key_passphrase': 'REPLACE_WITH_KEY_FILE_PASSPHRASE',
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
def ssh_contact(app_svc, contact_svc, data_svc, file_svc, obfuscator):
    services = app_svc.get_services()
    return SshTunnel(services)


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

    async def test_tunnel(self, ssh_contact):
        await ssh_contact.start()
        conn = await asyncssh.connect('127.0.0.1', port=8122, known_hosts=None, username='sandcat',
                                      password='s4ndc4t!', config=None)
        assert conn and conn.get_extra_info('username') == 'sandcat'
        listener = await conn.forward_local_port('', 61234, 'localhost', 8888)
        assert listener and listener.get_port() == 61234
        listener.close()
