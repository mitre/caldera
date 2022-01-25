import pytest
import os

from app.contacts import contact_ftp
from app.utility.base_world import BaseWorld

beacon_profile = {'architecture': 'amd64',
                  'contact': 'ftp',
                  'paw': '8924',
                  'exe_name': 'sandcat.exe',
                  'executors': ['cmd', 'psh'],
                  'group': 'red',
                  'host': 'testhost',
                  'location': 'C:\\sandcat.exe',
                  'pid': 1234,
                  'platform': 'windows',
                  'ppid': 123,
                  'privilege': 'User',
                  'username': 'testuser'
                  }


@pytest.fixture(scope='session')
def base_world():
    BaseWorld.clear_config()
    BaseWorld.apply_config(name='main', config={'app.contact.ftp.host': '0.0.0.0',
                                                'app.contact.ftp.port': '2222',
                                                'app.contact.ftp.pword': 'caldera',
                                                'app.contact.ftp.server.dir': 'ftp_dir',
                                                'app.contact.ftp.user': 'caldera_user',
                                                'plugins': ['sandcat', 'stockpile'],
                                                'crypt_salt': 'BLAH',
                                                'api_key': 'ADMIN123',
                                                'encryption_key': 'ADMIN123'})
    BaseWorld.apply_config(name='agents', config={'sleep_max': 5,
                                                  'sleep_min': 5,
                                                  'untrusted_timer': 90,
                                                  'watchdog': 0,
                                                  'implant_name': 'splunkd',
                                                  'bootstrap_abilities': [
                                                      '43b3754c-def4-4699-a673-1d85648fda6a'
                                                  ]})
    yield BaseWorld
    BaseWorld.clear_config()


@pytest.fixture
async def ftp_c2(app_svc, base_world, contact_svc, data_svc, file_svc, obfuscator):
    services = app_svc.get_services()
    ftp_c2 = contact_ftp.Contact(services)
    return ftp_c2


@pytest.fixture
def ftp_c2_my_server(ftp_c2):
    ftp_c2.set_up_server()
    return ftp_c2.server


class TestFtpServer:
    @staticmethod
    def test_server_setup(ftp_c2):
        assert ftp_c2.name == 'ftp'
        assert ftp_c2.description == 'Accept agent beacons through ftp'
        assert ftp_c2.host == '0.0.0.0'
        assert ftp_c2.port == '2222'
        assert ftp_c2.directory == 'ftp_dir'
        assert ftp_c2.user == 'caldera_user'
        assert ftp_c2.pword == 'caldera'
        assert ftp_c2.server is None

    @staticmethod
    def test_set_up_server(ftp_c2):
        ftp_c2.set_up_server()
        assert ftp_c2.server is not None

    @staticmethod
    def test_my_server_setup(ftp_c2_my_server):
        assert ftp_c2_my_server.host == '0.0.0.0'
        assert ftp_c2_my_server.port == '2222'
        assert ftp_c2_my_server.login == 'caldera_user'
        assert ftp_c2_my_server.pword == 'caldera'
        assert ftp_c2_my_server.ftp_server_dir == os.path.join(os.getcwd(), 'ftp_dir')
        assert os.path.exists(ftp_c2_my_server.ftp_server_dir)
        os.rmdir(ftp_c2_my_server.ftp_server_dir)
