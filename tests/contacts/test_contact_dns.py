import binascii
import json
import os
import pytest
import random

from base64 import b64decode
from dns import message, rdatatype

from app.contacts.contact_dns import Contact as DnsContact
from app.utility.base_world import BaseWorld
from app.utility.file_decryptor import read as decrypt_read, get_encryptor


@pytest.fixture(scope='session')
def dns_contact_base_world():
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


@pytest.fixture
async def dns_c2(app_svc, contact_svc, data_svc, file_svc, obfuscator):
    services = app_svc.get_services()
    dns_c2 = DnsContact(services)
    return dns_c2


@pytest.fixture
async def get_dns_response(dns_c2):
    async def _get_dns_response(qname, record_type):
        query_bytes = message.make_query(qname, record_type).to_wire()
        response_bytes = await dns_c2.handler.generate_dns_tunneling_response_bytes(query_bytes)
        return message.from_wire(response_bytes)
    return _get_dns_response


@pytest.fixture
def beacon_profile_hex_chunks(get_hex_chunks):
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
    return get_hex_chunks(marshaled.encode('utf-8'))


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
async def get_instruction_response(random_data, get_dns_response):
    async def _get_instruction_response(message_id):
        qname = '%s.id.0.1.%s.mycaldera.caldera' % (message_id, random_data)
        return await get_dns_response(qname, 'txt')
    return _get_instruction_response


@pytest.fixture
def get_hex_chunks():
    def _get_hex_chunks(data):
        hex_str = data.hex()
        chunk_size = 62
        hex_len = len(hex_str)
        return [hex_str[i:i + chunk_size] for i in range(0, hex_len, chunk_size)]
    return _get_hex_chunks


@pytest.fixture
def get_file_upload_metadata_qnames():
    def _get_file_upload_metadata_qnames(message_id, metadata_hex_chunks):
        num_chunks = len(metadata_hex_chunks)
        return ['%s.ur.%d.%d.%s.mycaldera.caldera' % (message_id, i, num_chunks, metadata_hex_chunks[i])
                for i in range(0, num_chunks)]
    return _get_file_upload_metadata_qnames


@pytest.fixture
def get_file_upload_data_qnames():
    def _get_file_upload_data_qnames(message_id, data_hex_chunks):
        num_chunks = len(data_hex_chunks)
        return ['%s.ud.%d.%d.%s.mycaldera.caldera' % (message_id, i, num_chunks, data_hex_chunks[i])
                for i in range(0, num_chunks)]
    return _get_file_upload_data_qnames


@pytest.mark.usefixtures(
    'dns_contact_base_world'
)
class TestContactDns:
    _RCODE_NXDOMAIN = 3
    _RCODE_SUCCESS = 0

    @staticmethod
    def _assert_successful_ivp4(response_msg):
        assert response_msg and response_msg.rcode() == TestContactDns._RCODE_SUCCESS

        # Make sure we got back an IPv4 address
        assert len(response_msg.answer) == 1
        assert len(response_msg.answer[0]) == 1
        assert response_msg.answer[0][0].rdtype == rdatatype.RdataType.A

    @staticmethod
    def _assert_even_ipv4(response_msg):
        # Last octet should be even if the server is expecting more data
        assert int(response_msg.answer[0][0].address.split('.')[3]) % 2 == 0

    @staticmethod
    def _assert_odd_ipv4(response_msg):
        # Last octet should be odd if the server received all data
        assert int(response_msg.answer[0][0].address.split('.')[3]) % 2 == 1

    def test_config(self, dns_c2):
        assert dns_c2.domain == 'mycaldera.caldera'

    def test_handler_setup(self, dns_c2):
        handler = dns_c2.handler
        assert handler.domain == 'mycaldera.caldera'
        assert handler.name == 'dns'

    async def test_non_c2_domain_message(self, get_dns_response):
        response_msg = await get_dns_response('notthec2domain', 'a')
        assert response_msg and response_msg.rcode() == self._RCODE_NXDOMAIN

    async def test_partial_beacon_message(self, get_dns_response, get_beacon_profile_qnames, message_id):
        first_qname = get_beacon_profile_qnames(message_id)[0]
        response_msg = await get_dns_response(first_qname, 'a')
        self._assert_successful_ivp4(response_msg)
        self._assert_even_ipv4(response_msg)

    async def test_completed_beacon_message(self, get_dns_response, get_beacon_profile_qnames, message_id):
        qnames = get_beacon_profile_qnames(message_id)
        final_index = len(qnames) - 1
        for index, qname in enumerate(qnames):
            response_msg = await get_dns_response(qname, 'a')
            self._assert_successful_ivp4(response_msg)

            # Check final octet
            if index == final_index:
                self._assert_odd_ipv4(response_msg)
            else:
                self._assert_even_ipv4(response_msg)

    async def test_instruction_download(self, get_dns_response, get_beacon_profile_qnames, message_id,
                                        get_instruction_response):
        # Send beacon before asking for instructions
        for qname in get_beacon_profile_qnames(message_id):
            await get_dns_response(qname, 'a')

        # Get instructions
        response_msg = await get_instruction_response(message_id)
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

    async def test_unsupported_client_request(self, get_dns_response, message_id, random_data):
        invalid_qname = '%s.invalid.0.1.%s.mycaldera.caldera' % (message_id, random_data)
        response_msg = await get_dns_response(invalid_qname, 'a')
        assert response_msg and response_msg.rcode() == self._RCODE_NXDOMAIN

    async def test_invalid_instruction_request(self, get_dns_response, message_id, random_data):
        invalid_qname = '%s.id.0.1.%s.mycaldera.caldera' % (message_id, random_data)
        response_msg = await get_dns_response(invalid_qname, 'a')  # Should be TXT request
        assert response_msg and response_msg.rcode() == self._RCODE_NXDOMAIN

    async def test_file_upload(self, get_dns_response, message_id, get_hex_chunks, get_file_upload_metadata_qnames,
                               get_file_upload_data_qnames):
        paw = 'asdasd'
        filename = 'testupload.txt'
        hostname = 'testhost'
        directory = '%s-%s' % (hostname, paw)
        upload_metadata = dict(paw=paw, file=filename, directory=directory)
        target_dir = '/tmp/%s' % directory
        target_path = '%s/%s-%s' % (target_dir, filename, message_id)
        file_data = b'thiswilltakemultiplednsrequests' * 100
        metadata_hex_chunks = get_hex_chunks(json.dumps(upload_metadata).encode('utf-8'))
        file_data_hex_chunks = get_hex_chunks(file_data)
        metadata_qnames = get_file_upload_metadata_qnames(message_id, metadata_hex_chunks)
        file_data_qnames = get_file_upload_data_qnames(message_id, file_data_hex_chunks)

        # Send file upload request
        final_index = len(metadata_qnames) - 1
        for index, qname in enumerate(metadata_qnames):
            response_msg = await get_dns_response(qname, 'a')
            self._assert_successful_ivp4(response_msg)
            # Check final octet
            if index == final_index:
                self._assert_odd_ipv4(response_msg)
            else:
                self._assert_even_ipv4(response_msg)

        # Send file data
        final_index = len(file_data_qnames) - 1
        for index, qname in enumerate(file_data_qnames):
            response_msg = await get_dns_response(qname, 'a')
            self._assert_successful_ivp4(response_msg)
            # Check final octet
            if index == final_index:
                self._assert_odd_ipv4(response_msg)
            else:
                self._assert_even_ipv4(response_msg)

        # Check if upload succeeded
        assert os.path.isfile(target_path)
        decrypt_error = None
        try:
            decrypted_upload = self._get_decrypted_upload(target_path)
        except Exception as e:
            decrypt_error = e
        finally:
            os.remove(target_path)
            os.rmdir(target_dir)
        assert (not decrypt_error), 'Exception occurred when decrypting uploaded file: %s' % decrypt_error
        assert file_data == decrypted_upload

    @staticmethod
    def _get_decrypted_upload(filepath):
        encryptor = get_encryptor('BLAH', 'ADMIN123')
        return decrypt_read(filepath, encryptor)

    def test_unexpected_file_upload(self):
        assert True
