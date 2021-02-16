import binascii
import json
import os
import pytest
import random

from base64 import b64decode
from dns import message, rdatatype

from app.contacts.contact_dns import Contact as DnsContact
from app.utility.base_world import BaseWorld


@pytest.fixture
def dns_c2(loop, app_svc, contact_svc, data_svc, obfuscator):
    BaseWorld.apply_config(name='main', config={'app.contact.dns.domain': 'mycaldera.caldera',
                                                'app.contact.dns.socket': '0.0.0.0:53',
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
    services = app_svc(loop).get_services()
    dns_c2 = DnsContact(services)
    return dns_c2


@pytest.fixture
def get_dns_response(loop, dns_c2):
    def _get_dns_response(qname, record_type):
        query_bytes = message.make_query(qname, record_type).to_wire()
        response_bytes = loop.run_until_complete(dns_c2.handler.generate_dns_tunneling_response_bytes(query_bytes))
        return message.from_wire(response_bytes)
    return _get_dns_response


@pytest.fixture(scope='class')
def beacon_profile_hex_chunks():
    beacon_profile = {
        'architecture': 'amd64',
        'contact': 'dns',
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
    marshaled = json.dumps(beacon_profile)
    hex_str = marshaled.encode('utf-8').hex()
    chunk_size = 62
    hex_len = len(hex_str)
    return [hex_str[i:i+chunk_size] for i in range(0, hex_len, chunk_size)]


@pytest.fixture
def message_id():
    return str(random.randrange(10000000, 100000000))


@pytest.fixture
def random_data():
    """Return 31 bytes of random hex data, encoded in a 62-char string"""
    return binascii.b2a_hex(os.urandom(31)).decode('utf-8')


@pytest.fixture
def get_beacon_profile_qnames(beacon_profile_hex_chunks):
    def _get_beacon_profile_qnames(message_id):
        num_chunks = len(beacon_profile_hex_chunks)
        return ['%s.be.%d.%d.%s.mycaldera.caldera' % (message_id, i, num_chunks, beacon_profile_hex_chunks[i])
                for i in range(0, num_chunks)]
    return _get_beacon_profile_qnames


@pytest.fixture
def get_instruction_response(random_data, get_dns_response):
    def _get_instruction_response(message_id):
        qname = '%s.id.0.1.%s.mycaldera.caldera' % (message_id, random_data)
        return get_dns_response(qname, 'txt')
    return _get_instruction_response


class TestContactDns:
    _RCODE_NXDOMAIN = 3
    _RCODE_SUCCESS = 0

    def test_config(self, dns_c2):
        assert dns_c2.domain == 'mycaldera.caldera'

    def test_handler_setup(self, dns_c2):
        handler = dns_c2.handler
        assert handler.domain == 'mycaldera.caldera'
        assert handler.name == 'dns'

    def test_non_c2_domain_message(self, get_dns_response):
        response_msg = get_dns_response('notthec2domain', 'a')
        assert response_msg and response_msg.rcode() == self._RCODE_NXDOMAIN

    def test_partial_beacon_message(self, get_dns_response, get_beacon_profile_qnames, message_id):
        first_qname = get_beacon_profile_qnames(message_id)[0]
        response_msg = get_dns_response(first_qname, 'a')
        assert response_msg and response_msg.rcode() == self._RCODE_SUCCESS

        # Make sure we got back an IPv4 address
        assert len(response_msg.answer) == 1
        assert len(response_msg.answer[0]) == 1
        assert response_msg.answer[0][0].rdtype == rdatatype.RdataType.A

        # Last octet should be even if the server is expecting more data
        assert int(response_msg.answer[0][0].address.split('.')[3]) % 2 == 0

    def test_completed_beacon_message(self, get_dns_response, get_beacon_profile_qnames, message_id):
        qnames = get_beacon_profile_qnames(message_id)
        final_index = len(qnames) - 1
        for index, qname in enumerate(qnames):
            response_msg = get_dns_response(qname, 'a')
            assert response_msg and response_msg.rcode() == self._RCODE_SUCCESS

            # Make sure we got back an IPv4 address
            assert len(response_msg.answer) == 1
            assert len(response_msg.answer[0]) == 1
            assert response_msg.answer[0][0].rdtype == rdatatype.RdataType.A

            # Check final octet
            final_octet = int(response_msg.answer[0][0].address.split('.')[3])
            if index == final_index:
                assert final_octet % 2 == 1
            else:
                assert final_octet % 2 == 0

    def test_instruction_download(self, get_dns_response, get_beacon_profile_qnames, message_id,
                                  get_instruction_response):
        # Send beacon before asking for instructions
        for qname in get_beacon_profile_qnames(message_id):
            get_dns_response(qname, 'a')

        # Get instructions
        response_msg = get_instruction_response(message_id)
        assert response_msg and response_msg.rcode() == self._RCODE_SUCCESS

        # Make sure we only get 1 TXT record
        assert len(response_msg.answer) == 1
        assert len(response_msg.answer[0]) == 1
        answer = response_msg.answer[0][0]
        assert answer.rdtype == rdatatype.RdataType.TXT
        assert len(answer.strings) == 1
        txt_response = answer.strings[0].decode('utf-8')

        # Last character should be , if returning complete instructions
        assert txt_response[-1] == ','
        beacon_resp = json.loads(b64decode(txt_response).decode('utf-8'))
        assert 'paw' in beacon_resp
        want = dict(paw=beacon_resp.get('paw'),
                    sleep=5,
                    watchdog=0,
                    instructions='[]')
        assert want == beacon_resp

    def test_unsupported_client_request(self, get_dns_response, message_id, random_data):
        invalid_qname = '%s.invalid.0.1.%s.mycaldera.caldera' % (message_id, random_data)
        response_msg = get_dns_response(invalid_qname, 'a')
        assert response_msg and response_msg.rcode() == self._RCODE_NXDOMAIN

    def test_invalid_instruction_request(self, get_dns_response, message_id, random_data):
        invalid_qname = '%s.id.0.1.%s.mycaldera.caldera' % (message_id, random_data)
        response_msg = get_dns_response(invalid_qname, 'a')  # Should be TXT request
        assert response_msg and response_msg.rcode() == self._RCODE_NXDOMAIN
