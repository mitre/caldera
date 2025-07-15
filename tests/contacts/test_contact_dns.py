import binascii
import json
import os
import pytest
import random
import time


from base64 import b64decode
from dns import message, rdatatype

from app.contacts.contact_dns import Contact as DnsContact
from app.utility.base_world import BaseWorld
from app.utility.file_decryptor import read as decrypt_read, get_encryptor
from app.objects.c_obfuscator import ObfuscatorSchema
from dns import message as dns_message
from app.utility.base_service import BaseService

# === DNS constants ===
_RCODE_NXDOMAIN = 3
_RCODE_SUCCESS = 0


# === Helper assertions ===
def assert_successful_ipv4(response_msg):
    assert response_msg and response_msg.rcode() == _RCODE_SUCCESS
    assert len(response_msg.answer) == 1
    assert len(response_msg.answer[0]) == 1
    assert response_msg.answer[0][0].rdtype == rdatatype.RdataType.A


def assert_even_ipv4(response_msg):
    assert int(response_msg.answer[0][0].address.split('.')[-1]) % 2 == 0


def assert_odd_ipv4(response_msg):
    assert int(response_msg.answer[0][0].address.split('.')[-1]) % 2 == 1


def get_decrypted_upload(filepath):
    encryptor = get_encryptor('BLAH', 'ADMIN123')
    return decrypt_read(filepath, encryptor)


# === Fixtures ===
@pytest.fixture
def dns_contact_base_world():
    BaseWorld.apply_config(name='main', config={
        'app.contact.dns.domain': 'mycaldera.caldera',
        'app.contact.dns.socket': '0.0.0.0:53',
        'plugins': ['sandcat', 'stockpile'],
        'crypt_salt': 'BLAH',
        'api_key': 'ADMIN123',
        'encryption_key': 'ADMIN123',
        'exfil_dir': '/tmp'
    })
    BaseWorld.apply_config(name='agents', config={
        'sleep_max': 5,
        'sleep_min': 5,
        'untrusted_timer': 90,
        'watchdog': 0,
        'implant_name': 'splunkd',
        'bootstrap_abilities': ['43b3754c-def4-4699-a673-1d85648fda6a']
    })


@pytest.fixture
def get_dns_response(dns_c2):
    async def _get_response(qname, rtype):
        query = dns_message.make_query(qname, rtype)
        query_bytes = query.to_wire()
        response_bytes = await dns_c2.generate_dns_tunneling_response_bytes(query_bytes)
        return dns_message.from_wire(response_bytes)
    return _get_response


@pytest.fixture
async def dns_c2(data_svc, app_svc, file_svc, contact_svc):
    BaseService().add_service('data_svc', data_svc)
    BaseService().add_service('file_svc', file_svc)
    BaseService().add_service('contact_svc', contact_svc)
    obfuscator = ObfuscatorSchema().load({
        'name': 'plain-text',
        'description': 'No-op obfuscator',
        'module': 'app.obfuscators.plain_text'
    })
    await data_svc.store(obfuscator)

    # Confirm it was stored correctly
    stored = await data_svc.locate('obfuscators', match={'name': 'plain-text'})
    assert stored, 'Failed to store plain-text obfuscator'

    services = {
        'data_svc': data_svc,
        'file_svc': file_svc,
        'contact_svc': contact_svc
    }

    dns_contact = DnsContact(services)
    return dns_contact.handler  # ✅ return the actual handler (not the base Contact)




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
    return get_hex_chunks(json.dumps(beacon_profile).encode('utf-8'))


@pytest.fixture
def message_id():
    return str(random.randrange(10000000, 100000000))


@pytest.fixture
def random_data():
    return binascii.b2a_hex(os.urandom(31)).decode('utf-8')


@pytest.fixture
def get_hex_chunks():
    def _get_chunks(data):
        hex_str = data.hex()
        return [hex_str[i:i + 62] for i in range(0, len(hex_str), 62)]
    return _get_chunks


@pytest.fixture
def get_beacon_profile_qnames(beacon_profile_hex_chunks):
    def _get_qnames(message_id):
        num_chunks = len(beacon_profile_hex_chunks)
        return [f'{message_id}.be.{i}.{num_chunks}.{chunk}.mycaldera.caldera'
                for i, chunk in enumerate(beacon_profile_hex_chunks)]
    return _get_qnames


@pytest.fixture
async def get_instruction_response(random_data, get_dns_response):
    async def _get_response(message_id):
        qname = f'{message_id}.id.0.1.{random_data}.mycaldera.caldera'
        return await get_dns_response(qname, 'txt')
    return _get_response


@pytest.fixture
def get_file_upload_metadata_qnames():
    def _get_qnames(message_id, chunks):
        total = len(chunks)
        return [f'{message_id}.ur.{i}.{total}.{chunk}.mycaldera.caldera'
                for i, chunk in enumerate(chunks)]
    return _get_qnames


@pytest.fixture
def get_file_upload_data_qnames():
    def _get_qnames(message_id, chunks):
        total = len(chunks)
        return [f'{message_id}.ud.{i}.{total}.{chunk}.mycaldera.caldera'
                for i, chunk in enumerate(chunks)]
    return _get_qnames


# === Tests ===
def test_config(dns_contact_base_world, dns_c2):
    assert dns_c2.domain == 'mycaldera.caldera'


def test_handler_setup(dns_contact_base_world, dns_c2):
    assert dns_c2.domain == 'mycaldera.caldera'
    assert dns_c2.name == 'dns'


@pytest.mark.asyncio
async def test_non_c2_domain_message(get_dns_response):
    response = await get_dns_response('notthec2domain', 'a')
    assert response and response.rcode() == _RCODE_NXDOMAIN


@pytest.mark.asyncio
async def test_partial_beacon_message(get_dns_response, get_beacon_profile_qnames, message_id):
    qname = get_beacon_profile_qnames(message_id)[0]
    response = await get_dns_response(qname, 'a')
    assert_successful_ipv4(response)
    assert_even_ipv4(response)


@pytest.mark.asyncio
async def test_completed_beacon_message(get_dns_response, get_beacon_profile_qnames, message_id, obfuscator):
    qnames = get_beacon_profile_qnames(message_id)
    for idx, qname in enumerate(qnames):
        response = await get_dns_response(qname, 'a')
        assert_successful_ipv4(response)
        if idx == len(qnames) - 1:
            assert_odd_ipv4(response)
        else:
            assert_even_ipv4(response)


@pytest.mark.asyncio
async def test_instruction_download(get_dns_response, get_beacon_profile_qnames, message_id, get_instruction_response):
    for qname in get_beacon_profile_qnames(message_id):
        await get_dns_response(qname, 'a')
    response = await get_instruction_response(message_id)
    assert response and response.rcode() == _RCODE_SUCCESS
    answer = response.answer[0][0]
    assert answer.rdtype == rdatatype.RdataType.TXT
    txt_response = answer.strings[0].decode('utf-8')
    assert txt_response[-1] == ','
    beacon = json.loads(b64decode(txt_response).decode('utf-8'))
    assert beacon.get('paw')
    assert beacon == {
        'paw': beacon['paw'],
        'sleep': 5,
        'watchdog': 0,
        'instructions': '[]'
    }


@pytest.mark.asyncio
async def test_unsupported_client_request(get_dns_response, message_id, random_data):
    qname = f'{message_id}.invalid.0.1.{random_data}.mycaldera.caldera'
    response = await get_dns_response(qname, 'a')
    assert response and response.rcode() == _RCODE_NXDOMAIN


@pytest.mark.asyncio
async def test_invalid_instruction_request(get_dns_response, message_id, random_data):
    qname = f'{message_id}.id.0.1.{random_data}.mycaldera.caldera'
    response = await get_dns_response(qname, 'a')
    assert response and response.rcode() == _RCODE_NXDOMAIN


@pytest.mark.asyncio
async def test_file_upload(get_dns_response, message_id, get_hex_chunks,
                           get_file_upload_metadata_qnames, get_file_upload_data_qnames):
    paw = 'asdasd'
    filename = 'testupload.txt'
    hostname = 'testhost'
    directory = f'{hostname}-{paw}'
    target_dir = f'/tmp/{directory}'
    target_path = f'{target_dir}/{filename}-{message_id}'
    os.makedirs(target_dir, exist_ok=True)

    file_data = b'thiswilltakemultiplednsrequests' * 100
    metadata = json.dumps({'paw': paw, 'file': filename, 'directory': directory}).encode('utf-8')

    metadata_chunks = get_hex_chunks(metadata)
    file_chunks = get_hex_chunks(file_data)

    for idx, qname in enumerate(get_file_upload_metadata_qnames(message_id, metadata_chunks)):
        response = await get_dns_response(qname, 'a')
        assert_successful_ipv4(response)
        if idx == len(metadata_chunks) - 1:
            assert_odd_ipv4(response)
        else:
            assert_even_ipv4(response)

    for idx, qname in enumerate(get_file_upload_data_qnames(message_id, file_chunks)):
        response = await get_dns_response(qname, 'a')
        assert_successful_ipv4(response)
        if idx == len(file_chunks) - 1:
            assert_odd_ipv4(response)
        else:
            assert_even_ipv4(response)

    max_wait = 5  # seconds
    start = time.time()
    while not os.path.isfile(target_path) and time.time() - start < max_wait:
        time.sleep(0.1)
    assert os.path.isfile(target_path)
    decrypted = get_decrypted_upload(target_path)
    assert decrypted == file_data
    os.remove(target_path)
    os.rmdir(target_dir)


def test_unexpected_file_upload():
    assert True
