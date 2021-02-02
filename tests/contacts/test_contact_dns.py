import pytest

from app.contacts.contact_dns import Contact as DnsContact
from app.utility.base_world import BaseWorld


@pytest.fixture
def dns_c2(loop, app_svc):
    BaseWorld.apply_config(name='main', config={'app.contact.dns.domain': 'mycaldera.caldera',
                                                'app.contact.dns.socket': '0.0.0.0:53',
                                                'plugins': ['sandcat', 'stockpile'],
                                                'crypt_salt': 'BLAH',
                                                'api_key': 'ADMIN123',
                                                'encryption_key': 'ADMIN123',
                                                'exfil_dir': '/tmp'})
    services = app_svc(loop).get_services()
    dns_c2 = DnsContact(services)
    return dns_c2


class TestContactDns:
    def test_config(self, dns_c2):
        assert dns_c2.domain == 'mycaldera.caldera'

    def test_handler_setup(self, dns_c2):
        handler = dns_c2.handler
        assert handler.domain == 'mycaldera.caldera'
        assert handler.name == 'dns'
