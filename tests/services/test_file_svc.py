import os
import pytest
import yaml

from base64 import b64encode
from tests import AsyncMock
from asyncio import Future

from app.objects.c_data_encoder import DataEncoder
from app.objects.c_operation import Operation
from app.objects.secondclass.c_link import Link
from app.utility.file_decryptor import decrypt


@pytest.mark.usefixtures(
    'init_base_world'
)
class TestFileService:

    def test_save_file(self, loop, file_svc, tmp_path):
        filename = "test_file.txt"
        payload = b'These are the file contents.'
        # Save temporary test file
        loop.run_until_complete(file_svc.save_file(filename, payload, tmp_path, encrypt=False))
        file_location = tmp_path / filename
        # Read file contents from saved file
        file_contents = open(file_location, "r")
        assert os.path.isfile(file_location)
        assert payload.decode("utf-8") == file_contents.read()

    def test_create_exfil_sub_directory(self, loop, file_svc):
        exfil_dir_name = 'unit-testing-Rocks'
        new_dir = loop.run_until_complete(file_svc.create_exfil_sub_directory(exfil_dir_name))
        assert os.path.isdir(new_dir)
        os.rmdir(new_dir)

    def test_read_write_result_file(self, tmpdir, file_svc):
        link_id = '12345'
        output = 'output testing unit'
        # write output data
        file_svc.write_result_file(link_id=link_id, output=output, location=tmpdir)

        # read output data
        output_data = file_svc.read_result_file(link_id=link_id, location=tmpdir)
        assert output_data == output

    def test_upload_decode_plaintext(self, loop, file_svc, data_svc, ability):
        loop.run_until_complete(data_svc.store(
            DataEncoder(name='plain-text',
                        description='Does not encode or decode data at all, instead keeps it in plain text form',
                        module='tests.services.data_encoders.plain_text')
        ))
        test_ability = ability(ability_id='123')
        test_link = Link(command='net user a', paw='123456', ability=test_ability, id=123456,
                         file_encoding='plain-text')
        op = Operation(name='test op plaintext', agents=[], adversary=None, id='12345')
        op.chain = [test_link]
        loop.run_until_complete(data_svc.store(op))
        file_svc.data_svc = data_svc
        upload_dir = loop.run_until_complete(file_svc.create_exfil_sub_directory('test-plaintext-upload'))
        upload_filename = 'plaintext.txt'
        upload_content = b'this will be encoded and decoded as plaintext'
        loop.run_until_complete(file_svc.save_file(upload_filename, upload_content, upload_dir, encrypt=False,
                                                   link_id=test_link.id))
        uploaded_file_path = os.path.join(upload_dir, upload_filename)
        assert os.path.isfile(uploaded_file_path)
        with open(uploaded_file_path, 'rb') as file:
            written_data = file.read()
        assert written_data == upload_content
        os.remove(uploaded_file_path)
        os.rmdir(upload_dir)

    def test_upload_decode_b64(self, loop, file_svc, data_svc, ability):
        loop.run_until_complete(data_svc.store(
            DataEncoder(name='base64',
                        description='Encodes and decodes data in base64',
                        module='tests.services.data_encoders.base64_basic')
        ))
        test_ability = ability(ability_id='456')
        test_link = Link(command='net user a', paw='123456', ability=test_ability, id=123457,
                         file_encoding='base64')
        op = Operation(name='test op b64', agents=[], adversary=None, id='12346')
        op.chain = [test_link]
        loop.run_until_complete(data_svc.store(op))
        file_svc.data_svc = data_svc
        upload_dir = loop.run_until_complete(file_svc.create_exfil_sub_directory('test-base64-upload'))
        upload_filename = 'base64.txt'
        original_content = b'this will be encoded and decoded as base64'
        upload_content = b64encode(original_content)
        loop.run_until_complete(file_svc.save_file(upload_filename, upload_content, upload_dir, encrypt=False,
                                                   link_id=test_link.id))
        uploaded_file_path = os.path.join(upload_dir, upload_filename)
        assert os.path.isfile(uploaded_file_path)
        with open(uploaded_file_path, 'rb') as file:
            written_data = file.read()
        assert written_data == original_content
        os.remove(uploaded_file_path)
        os.rmdir(upload_dir)

    def test_download_plaintext_file(self, loop, file_svc):
        filename = 'plaintextpayload.txt'
        payload_content = b'plaintext content'
        file_svc.read_file = AsyncMock(return_value=(filename, payload_content))
        file_path, content, display_name = loop.run_until_complete(
            file_svc.get_file(headers={'file': filename, 'file-encoding': 'plain-text'})
        )
        assert file_path == filename
        assert content == payload_content
        assert display_name == filename

    def test_download_base64_file(self, loop, file_svc):
        filename = 'b64payload.txt'
        payload_content = b'b64 content'
        file_svc.read_file = AsyncMock(return_value=(filename, payload_content))
        file_path, content, display_name = loop.run_until_complete(
            file_svc.get_file(headers={'file': filename, 'file-encoding': 'base64'})
        )
        assert file_path == filename
        assert content == b64encode(payload_content)
        assert display_name == filename

    def test_pack_file(self, loop, mocker, tmpdir, file_svc, data_svc):
        payload = 'unittestpayload'
        payload_content = b'content'
        new_payload_content = b'new_content'
        packer_name = 'test'

        # create temp files
        file = tmpdir.join(payload)
        file.write(payload_content)

        # start mocking up methods
        packer = mocker.Mock(return_value=Future())
        packer.return_value = packer
        packer.pack = AsyncMock(return_value=(payload, new_payload_content))
        data_svc.locate = AsyncMock(return_value=[])
        module = mocker.Mock()
        module.Packer = packer
        file_svc.packers[packer_name] = module
        file_svc.data_svc = data_svc
        file_svc.read_file = AsyncMock(return_value=(payload, payload_content))

        file_path, content, display_name = loop.run_until_complete(file_svc.get_file(headers=dict(file='%s:%s' % (packer_name, payload))))

        packer.pack.assert_called_once()
        assert payload == file_path
        assert content == new_payload_content

    def test_upload_file(self, loop, file_svc):
        upload_dir = loop.run_until_complete(file_svc.create_exfil_sub_directory('test-upload'))
        upload_filename = 'uploadedfile.txt'
        upload_content = b'this is a test upload file'
        loop.run_until_complete(file_svc.save_file(upload_filename, upload_content, upload_dir, encrypt=False))
        uploaded_file_path = os.path.join(upload_dir, upload_filename)
        assert os.path.isfile(uploaded_file_path)
        with open(uploaded_file_path, 'rb') as file:
            written_data = file.read()
        assert written_data == upload_content
        os.remove(uploaded_file_path)
        os.rmdir(upload_dir)

    def test_encrypt_upload(self, loop, file_svc):
        upload_dir = loop.run_until_complete(file_svc.create_exfil_sub_directory('test-encrypted-upload'))
        upload_filename = 'encryptedupload.txt'
        upload_content = b'this is a test upload file'
        loop.run_until_complete(file_svc.save_file(upload_filename, upload_content, upload_dir))
        uploaded_file_path = os.path.join(upload_dir, upload_filename)
        decrypted_file_path = upload_filename + '_decrypted'
        config_to_use = 'conf/default.yml'
        with open(config_to_use, encoding='utf-8') as conf:
            config = list(yaml.load_all(conf, Loader=yaml.FullLoader))[0]
        decrypt(uploaded_file_path, config, output_file=decrypted_file_path)
        assert os.path.isfile(decrypted_file_path)
        with open(decrypted_file_path, 'rb') as decrypted_file:
            decrypted_data = decrypted_file.read()
        assert decrypted_data == upload_content
        os.remove(uploaded_file_path)
        os.remove(decrypted_file_path)
        os.rmdir(upload_dir)
