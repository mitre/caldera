import os
import pytest
import yaml

from base64 import b64encode
from tests import AsyncMock
from unittest import mock
from asyncio import Future

from app.data_encoders.base64_basic import Base64Encoder
from app.data_encoders.plain_text import PlainTextEncoder
from app.objects.secondclass.c_link import Link
from app.utility.file_decryptor import decrypt


@pytest.fixture
def store_encoders(loop, data_svc):
    loop.run_until_complete(data_svc.store(PlainTextEncoder()))
    loop.run_until_complete(data_svc.store(Base64Encoder()))


@pytest.mark.usefixtures(
    'init_base_world',
    'store_encoders'
)
class TestFileService:

    @pytest.fixture
    def text_file(self, tmpdir):
        txt_str = 'Hello world!'
        f = tmpdir.mkdir('txt').join('test.txt')
        f.write(txt_str)
        assert f.read() == txt_str
        yield f

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

    def test_upload_decode_plaintext(self, loop, file_svc, data_svc, app_svc):
        content = b'this will be encoded and decoded as plaintext'
        self._test_upload_file_with_encoding_via_link(loop, file_svc, data_svc, app_svc, encoding='plain-text',
                                                      upload_content=content, decoded_content=content)
        self._test_upload_file_with_encoding(loop, file_svc, data_svc, encoding='plain-text', upload_content=content,
                                             decoded_content=content)

    def test_upload_decode_b64(self, loop, file_svc, data_svc, app_svc):
        original_content = b'this will be encoded and decoded as base64'
        upload_content = b64encode(original_content)
        self._test_upload_file_with_encoding_via_link(loop, file_svc, data_svc, app_svc, encoding='base64',
                                                      upload_content=upload_content, decoded_content=original_content)
        self._test_upload_file_with_encoding(loop, file_svc, data_svc, encoding='base64', upload_content=upload_content,
                                             decoded_content=original_content)

    def test_download_plaintext_file(self, loop, file_svc, data_svc, app_svc):
        payload_content = b'plaintext content'
        self._test_download_file_with_encoding(loop, file_svc, encoding='plain-text', original_content=payload_content,
                                               encoded_content=payload_content)
        self._test_download_file_with_encoding_via_link(loop, file_svc, data_svc, app_svc, encoding='plain-text',
                                                        original_content=payload_content,
                                                        encoded_content=payload_content)

    def test_download_base64_file(self, loop, file_svc, data_svc, app_svc):
        payload_content = b'b64 content'
        self._test_download_file_with_encoding(loop, file_svc, encoding='base64', original_content=payload_content,
                                               encoded_content=b64encode(payload_content))
        self._test_download_file_with_encoding_via_link(loop, file_svc, data_svc, app_svc, encoding='base64',
                                                        original_content=payload_content,
                                                        encoded_content=b64encode(payload_content))

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

    def test_xored_filename_removal(self, loop, mocker, tmpdir, file_svc, data_svc):
        payload = 'unittestpayload.exe.xored'
        payload_content = b'content'
        new_payload_content = b'new_content'
        packer_name = 'test_xored_filename_removal'
        expected_display_name = 'unittestpayload.exe'

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
        assert display_name == expected_display_name

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

    def test_walk_file_path_exists_nonxor(self, loop, text_file, file_svc):
        ret = loop.run_until_complete(file_svc.walk_file_path(text_file.dirname, text_file.basename))
        assert ret == text_file

    def test_walk_file_path_notexists(self, loop, text_file, file_svc):
        ret = loop.run_until_complete(file_svc.walk_file_path(text_file.dirname, 'not-a-real.file'))
        assert ret is None

    def test_walk_file_path_xor_fn(self, loop, tmpdir, file_svc):
        f = tmpdir.mkdir('txt').join('xorfile.txt.xored')
        f.write("test")
        ret = loop.run_until_complete(file_svc.walk_file_path(f.dirname, 'xorfile.txt'))
        assert ret == f

    def test_remove_xored_extension(self, file_svc):
        test_value = 'example_file.exe.xored'
        expected_value = 'example_file.exe'
        ret = file_svc.remove_xored_extension(test_value)
        assert ret == expected_value

    def test_remove_xored_extension_to_non_xored_file(self, file_svc):
        test_value = 'example_file.exe'
        expected_value = 'example_file.exe'
        ret = file_svc.remove_xored_extension(test_value)
        assert ret == expected_value

    def test_add_xored_extension(self, file_svc):
        test_value = 'example_file.exe'
        expected_value = 'example_file.exe.xored'
        ret = file_svc.add_xored_extension(test_value)
        assert ret == expected_value

    def test_add_xored_extension_to_xored_file(self, file_svc):
        test_value = 'example_file.exe.xored'
        expected_value = 'example_file.exe.xored'
        ret = file_svc.add_xored_extension(test_value)
        assert ret == expected_value

    def test_is_extension_xored_true(self, file_svc):
        test_value = 'example_file.exe.xored'
        ret = file_svc.is_extension_xored(test_value)
        assert ret is True

    def test_is_extension_xored_false(self, file_svc):
        test_value = 'example_file.exe'
        ret = file_svc.is_extension_xored(test_value)
        assert ret is False

    @staticmethod
    def _test_download_file_with_encoding(loop, file_svc, encoding, original_content, encoded_content):
        filename = 'testencodedpayload.txt'
        file_svc.read_file = AsyncMock(return_value=(filename, original_content))
        file_path, content, display_name = loop.run_until_complete(
            file_svc.get_file(headers={'file': filename, 'x-file-encoding': encoding})
        )
        assert file_path == filename
        assert content == encoded_content
        assert display_name == filename

    @staticmethod
    def _test_download_file_with_encoding_via_link(loop, file_svc, data_svc, app_svc, encoding, original_content,
                                                   encoded_content):
        def _mocked_get_service(requested_service):
            if requested_service == 'app_svc':
                return app_svc
            else:
                return file_svc.get_services().get(requested_service)

        test_link = Link(command='net user a', paw='123456', ability=None, executor=None, id=123456,
                         file_encoding=encoding)
        app_svc.find_link = AsyncMock(return_value=test_link)
        file_svc.get_service = mock.Mock(side_effect=_mocked_get_service)
        file_svc.data_svc = data_svc
        filename = 'testencodedpayload.txt'
        file_svc.read_file = AsyncMock(return_value=(filename, original_content))
        file_path, content, display_name = loop.run_until_complete(
            file_svc.get_file(headers={'file': filename, 'x-link-id': test_link.id})
        )
        assert file_path == filename
        assert content == encoded_content
        assert display_name == filename

    @staticmethod
    def _test_upload_file_with_encoding(loop, file_svc, data_svc, encoding, upload_content, decoded_content):
        file_svc.data_svc = data_svc
        upload_dir = loop.run_until_complete(file_svc.create_exfil_sub_directory('testencodeduploaddir'))
        upload_filename = 'testencodedupload.txt'
        loop.run_until_complete(file_svc.save_file(upload_filename, upload_content, upload_dir, encrypt=False,
                                                   encoding=encoding))
        uploaded_file_path = os.path.join(upload_dir, upload_filename)
        assert os.path.isfile(uploaded_file_path)
        with open(uploaded_file_path, 'rb') as file:
            written_data = file.read()
        assert written_data == decoded_content
        os.remove(uploaded_file_path)
        os.rmdir(upload_dir)

    @staticmethod
    def _test_upload_file_with_encoding_via_link(loop, file_svc, data_svc, app_svc, encoding, upload_content,
                                                 decoded_content):
        def _mocked_get_service(requested_service):
            if requested_service == 'app_svc':
                return app_svc
            else:
                return file_svc.get_services().get(requested_service)

        test_link = Link(command='net user a', paw='123456', ability=None, executor=None, id=123456,
                         file_encoding=encoding)
        app_svc.find_link = AsyncMock(return_value=test_link)
        file_svc.get_service = mock.Mock(side_effect=_mocked_get_service)
        file_svc.data_svc = data_svc
        upload_dir = loop.run_until_complete(file_svc.create_exfil_sub_directory('testencodeduploaddir'))
        upload_filename = 'testencodedupload.txt'
        loop.run_until_complete(file_svc.save_file(upload_filename, upload_content, upload_dir, encrypt=False,
                                                   link_id=test_link.id))
        uploaded_file_path = os.path.join(upload_dir, upload_filename)
        assert os.path.isfile(uploaded_file_path)
        with open(uploaded_file_path, 'rb') as file:
            written_data = file.read()
        assert written_data == decoded_content
        os.remove(uploaded_file_path)
        os.rmdir(upload_dir)
