import binascii
import json
import os
import pytest
import random
import shutil

from base64 import b64decode
from dns import message, rdatatype
from unittest import mock

from app.contacts.contact_dns import Contact as DnsContact
from app.contacts.contact_dns import DnsPacket, DnsResponse, DnsAnswerObj, DnsRecordType, DnsResponseCodes
from app.objects.c_agent import Agent
from app.service.contact_svc import ContactService
from app.service.file_svc import FileSvc
from app.utility.base_world import BaseWorld
from app.utility.file_decryptor import read as decrypt_read, get_encryptor


DNS_EXFIL_DIR = '/tmp/testdnsexfil'


@pytest.fixture(scope='session')
def dns_contact_base_world():
    BaseWorld.clear_config()
    BaseWorld.apply_config(name='main', config={'app.contact.dns.domain': 'mycaldera.caldera',
                                                'app.contact.dns.socket': '127.0.0.1:65053',
                                                'plugins': ['sandcat', 'stockpile'],
                                                'crypt_salt': 'BLAH',
                                                'api_key': 'ADMIN123',
                                                'encryption_key': 'ADMIN123',
                                                'exfil_dir': DNS_EXFIL_DIR})
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
    if os.path.exists(DNS_EXFIL_DIR):
        shutil.rmtree(DNS_EXFIL_DIR)


@pytest.fixture
async def dns_c2(app_svc, contact_svc, data_svc, file_svc, obfuscator, dns_contact_base_world):
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
async def get_payload_filename(random_data, get_dns_response):
    async def _get_payload_filename(message_id):
        qname = '%s.pf.0.1.%s.mycaldera.caldera' % (message_id, random_data)
        return await get_dns_response(qname, 'txt')
    return _get_payload_filename


@pytest.fixture
async def get_payload_data(random_data, get_dns_response):
    async def _get_payload_data(message_id):
        qname = '%s.pd.0.1.%s.mycaldera.caldera' % (message_id, random_data)
        return await get_dns_response(qname, 'txt')
    return _get_payload_data


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


@pytest.fixture
def get_payload_request_qnames():
    def _get_payload_request_qnames(message_id, data_hex_chunks):
        num_chunks = len(data_hex_chunks)
        return ['%s.pr.%d.%d.%s.mycaldera.caldera' % (message_id, i, num_chunks, data_hex_chunks[i])
                for i in range(0, num_chunks)]
    return _get_payload_request_qnames


@pytest.fixture
def dns_dummy_agent():
    return Agent(paw='testpaw', sleep_min=5, sleep_max=5, watchdog=0, executors=['sh', 'proc'])


class TestDnsAuxiliary:
    def test_generate_packets_from_bytes(self):
        # Request
        packet_bytes = bytes([
            0x02, 0x83, 0x01, 0x00, 0x00, 0x01, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x06, 0x67, 0x6f, 0x6f,
            0x67, 0x6c, 0x65, 0x03, 0x63, 0x6f, 0x6d, 0x00,
            0x00, 0x01, 0x00, 0x01
        ])

        query_packet = DnsPacket.generate_packet_from_bytes(packet_bytes)
        want_str = '''Qname: google.com
Is query: True
Is response: False
Transaction ID: 0x0283
Flags: 0x0100
Num questions: 1
Num answer resource records: 0
Num auth resource records: 0
Num additional resource records: 0
Record type: 1
Class: 1
Standard query: True
Opcode: 0x0000
Response code: 0x0000
Recursion desired: True
Recursion available: False
Truncated: False'''
        assert str(query_packet) == want_str

        # Response
        packet_bytes = bytes([
            0x02, 0x83, 0x81, 0x80, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x06, 0x67, 0x6f, 0x6f,
            0x67, 0x6c, 0x65, 0x03, 0x63, 0x6f, 0x6d, 0x00, 0x00, 0x01, 0x00, 0x01, 0xc0, 0x0c, 0x00, 0x01,
            0x00, 0x01, 0x00, 0x00, 0x00, 0x69, 0x00, 0x04, 0xac, 0xfd, 0x8b, 0x8a, 0xc0, 0x0c, 0x00, 0x01,
            0x00, 0x01, 0x00, 0x00, 0x00, 0x69, 0x00, 0x04, 0xac, 0xfd, 0x8b, 0x71, 0xc0, 0x0c, 0x00, 0x01,
            0x00, 0x01, 0x00, 0x00, 0x00, 0x69, 0x00, 0x04, 0xac, 0xfd, 0x8b, 0x64, 0xc0, 0x0c, 0x00, 0x01,
            0x00, 0x01, 0x00, 0x00, 0x00, 0x69, 0x00, 0x04, 0xac, 0xfd, 0x8b, 0x65, 0xc0, 0x0c, 0x00, 0x01,
            0x00, 0x01, 0x00, 0x00, 0x00, 0x69, 0x00, 0x04, 0xac, 0xfd, 0x8b, 0x66, 0xc0, 0x0c, 0x00, 0x01,
            0x00, 0x01, 0x00, 0x00, 0x00, 0x69, 0x00, 0x04, 0xac, 0xfd, 0x8b, 0x8b
        ])
        resp_packet = DnsPacket.generate_packet_from_bytes(packet_bytes)
        want_str = '''Qname: google.com
Is query: False
Is response: True
Transaction ID: 0x0283
Flags: 0x8180
Num questions: 1
Num answer resource records: 1
Num auth resource records: 0
Num additional resource records: 0
Record type: 1
Class: 1
Standard query: True
Opcode: 0x0000
Response code: 0x0000
Recursion desired: True
Recursion available: True
Truncated: False'''
        assert str(resp_packet) == want_str

        dummy_answer = DnsAnswerObj(DnsRecordType.A, 0x1, 105, bytes([0xac, 0xfd, 0x8b, 0x8a]))
        response = DnsResponse.generate_response_for_query(query_packet, DnsResponseCodes.SUCCESS, [dummy_answer], authoritative=False,
                                                           recursion_available=True, truncated=False)
        want_str = '''Qname: google.com
Is query: False
Is response: True
Transaction ID: 0x0283
Flags: 0x8180
Num questions: 1
Num answer resource records: 1
Num auth resource records: 0
Num additional resource records: 0
Record type: 1
Class: 1
Standard query: True
Opcode: 0x0000
Response code: 0x0000
Recursion desired: True
Recursion available: True
Truncated: False
Answers:
    Record type: 1
    Dns class: 1
    TTL: 105
    Data: acfd8b8a
    Data length: 4
'''
        assert str(response) == want_str


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
    def _assert_nxdomain_response(response_msg):
        assert response_msg and response_msg.rcode() == TestContactDns._RCODE_NXDOMAIN
        assert len(response_msg.answer) == 0

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
        self._assert_nxdomain_response(response_msg)

    async def test_partial_beacon_message(self, get_dns_response, get_beacon_profile_qnames, message_id):
        first_qname = get_beacon_profile_qnames(message_id)[0]
        response_msg = await get_dns_response(first_qname, 'a')
        self._assert_successful_ivp4(response_msg)
        self._assert_even_ipv4(response_msg)

    async def test_completed_beacon_message(self, get_dns_response, get_beacon_profile_qnames, message_id, event_svc, fire_event_mock):
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
                                        get_instruction_response, dns_dummy_agent):
        with mock.patch.object(ContactService, 'handle_heartbeat', return_value=(dns_dummy_agent, [])):
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
        beacon_resp = json.loads(b64decode(txt_response[:-1]).decode('utf-8'))
        assert 'paw' in beacon_resp
        want = dict(paw='testpaw',
                    sleep=5,
                    watchdog=0,
                    instructions='[]')
        assert want == beacon_resp

    async def test_payload_download(self, get_dns_response, get_hex_chunks, get_payload_request_qnames, get_payload_filename, 
                                    get_payload_data, message_id):
        dummy_payload_data = bytes([0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef])
        with mock.patch.object(FileSvc, 'get_file', return_value=('testplugin/payloads/testdownload', dummy_payload_data, 'testdownload')):
            # Request payload
            filename = 'testdownload'
            req_metadata = dict(file=filename)
            metadata_hex_chunks = get_hex_chunks(json.dumps(req_metadata).encode('utf-8'))
            metadata_qnames = get_payload_request_qnames(message_id, metadata_hex_chunks)
            final_index = len(metadata_qnames) - 1

            for index, qname in enumerate(metadata_qnames):
                response_msg = await get_dns_response(qname, 'a')
                assert response_msg and response_msg.rcode() == self._RCODE_SUCCESS

                # Check final octet
                if index == final_index:
                    self._assert_odd_ipv4(response_msg)
                else:
                    self._assert_even_ipv4(response_msg)

        # Fetch payload name
        response_msg = await get_payload_filename(message_id)
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
        assert filename == b64decode(txt_response[:-1]).decode('utf-8')

        # Fetch payload data
        response_msg = await get_payload_data(message_id)
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
        assert dummy_payload_data == b64decode(txt_response[:-1])

    async def test_bad_payload_download(self, get_dns_response, get_hex_chunks, get_payload_request_qnames, message_id):
        # Test file service exceptions
        filename = 'testdownload'
        req_metadata = dict(file=filename)
        metadata_hex_chunks = get_hex_chunks(json.dumps(req_metadata).encode('utf-8'))
        metadata_qnames = get_payload_request_qnames(message_id, metadata_hex_chunks)
        final_index = len(metadata_qnames) - 1

        with mock.patch.object(FileSvc, 'get_file', side_effect=FileNotFoundError('Dummy error')):
            for index, qname in enumerate(metadata_qnames):
                response_msg = await get_dns_response(qname, 'a')

                # Check final octet
                if index == final_index:
                    self._assert_nxdomain_response(response_msg)
                else:
                    self._assert_even_ipv4(response_msg)

        with mock.patch.object(FileSvc, 'get_file', side_effect=Exception('Dummy error')):
            for index, qname in enumerate(metadata_qnames):
                response_msg = await get_dns_response(qname, 'a')

                # Check final octet
                if index == final_index:
                    self._assert_nxdomain_response(response_msg)
                else:
                    self._assert_even_ipv4(response_msg)

        # Test bad requests
        req_metadata = [dict(), dict(a='irrelevant')]
        for metadata in req_metadata:
            metadata_hex_chunks = get_hex_chunks(json.dumps(metadata).encode('utf-8'))
            metadata_qnames = get_payload_request_qnames(message_id, metadata_hex_chunks)
            final_index = len(metadata_qnames) - 1
            for index, qname in enumerate(metadata_qnames):
                response_msg = await get_dns_response(qname, 'a')

                # Check final octet
                if index == final_index:
                    self._assert_nxdomain_response(response_msg)
                else:
                    self._assert_even_ipv4(response_msg)

    async def test_unsupported_client_request(self, get_dns_response, message_id, random_data):
        invalid_qname = '%s.invalid.0.1.%s.mycaldera.caldera' % (message_id, random_data)
        response_msg = await get_dns_response(invalid_qname, 'a')
        self._assert_nxdomain_response(response_msg)

    async def test_invalid_instruction_request(self, get_dns_response, message_id, random_data):
        invalid_qname = '%s.id.0.1.%s.mycaldera.caldera' % (message_id, random_data)
        response_msg = await get_dns_response(invalid_qname, 'a')  # Should be TXT request
        self._assert_nxdomain_response(response_msg)

    async def test_file_upload(self, get_dns_response, message_id, get_hex_chunks, get_file_upload_metadata_qnames,
                               get_file_upload_data_qnames, dns_c2):
        dns_c2.set_config('main', 'exfil_dir', DNS_EXFIL_DIR)
        paw = 'asdasd'
        filename = 'testupload.txt'
        hostname = 'testhost'
        directory = '%s-%s' % (hostname, paw)
        upload_metadata = dict(paw=paw, file=filename, directory=directory)
        target_dir = f'{DNS_EXFIL_DIR}/{directory}'
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

    async def test_bad_file_upload(self, get_dns_response, message_id, get_hex_chunks, get_file_upload_metadata_qnames,
                                   get_file_upload_data_qnames):
        # Test missing info
        upload_metadata = [dict(paw='test'), dict()]
        for metadata in upload_metadata:
            metadata_hex_chunks = get_hex_chunks(json.dumps(metadata).encode('utf-8'))
            metadata_qnames = get_file_upload_metadata_qnames(message_id, metadata_hex_chunks)
            final_index = len(metadata_qnames) - 1
            for index, qname in enumerate(metadata_qnames):
                response_msg = await get_dns_response(qname, 'a')

                if index == final_index:
                    self._assert_nxdomain_response(response_msg)
                else:
                    self._assert_successful_ivp4(response_msg)
                    self._assert_even_ipv4(response_msg)

    async def test_ipv6_placeholder(self, dns_c2, get_dns_response):
        response_msg = await get_dns_response('test.mycaldera.caldera', rdatatype.RdataType.AAAA)
        assert response_msg and response_msg.rcode() == TestContactDns._RCODE_SUCCESS

        # Make sure we got back an IPv6 address
        assert len(response_msg.answer) == 1
        assert len(response_msg.answer[0]) == 1
        assert response_msg.answer[0][0].rdtype == rdatatype.RdataType.AAAA

    @staticmethod
    def _get_decrypted_upload(filepath):
        encryptor = get_encryptor('BLAH', 'ADMIN123')
        return decrypt_read(filepath, encryptor)
