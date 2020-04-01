import os
import pytest

from app.utility.payload_encoder import xor_file
from tests import AsyncMock


@pytest.mark.usefixtures(
    'init_base_world'
)
class TestFileService:

    @pytest.mark.skip
    @pytest.fixture
    def setup_mock_dataservice(self, mocker):
        pass

    def test_get_file_no_file_header(self, loop, file_svc):
        with pytest.raises(KeyError):
            loop.run_until_complete(file_svc.get_file(headers=dict()))

    @pytest.mark.skip('remove mocking')
    def test_get_file_special_payload(self, loop, mocker, file_svc):
        payload = 'unittestpayload'
        new_payload_name = 'utp'
        payload_content = b'content'
        payload_func = AsyncMock(return_value=(payload, new_payload_name))

        # patch out read_file and special payload for testing
        mocker.patch.object(file_svc, 'read_file', new_callable=AsyncMock, return_value=(payload, payload_content))
        mocker.patch.dict(file_svc.special_payloads, {payload: payload_func})

        fp, rcontent, display_name = loop.run_until_complete(file_svc.get_file(headers=dict(file=payload, name=new_payload_name)))

        payload_func.assert_called_once()
        assert display_name == new_payload_name
        assert rcontent == payload_content
        assert payload in fp

    @pytest.mark.skip('remove mocking')
    def test_save_get_file(self, loop, mocker, file_svc):
        filename = 'unittest-file-save-test'
        content = b'content!'
        path = 'data'

        # create and save a file
        data_svc = mocker.Mock()
        data_svc.locate = AsyncMock(return_value=[])
        mocker.patch.object(file_svc, 'data_svc', new=data_svc)
        loop.run_until_complete(file_svc.save_file(filename, content, path))
        assert os.path.isfile('./%s/%s' % (path, filename))

        # get and check contents
        fp, rcontent, display_name = loop.run_until_complete(file_svc.get_file(headers=dict(file=filename)))
        assert fp == filename
        assert rcontent == content
        assert display_name == filename

        # delete file
        os.remove('./%s/%s' % (path, filename))

    def test_create_exfil_sub_directory(self, loop, file_svc):
        exfil_dir_name = 'unit-testing-Rocks'
        new_dir = loop.run_until_complete(file_svc.create_exfil_sub_directory(exfil_dir_name))
        assert os.path.isdir(new_dir)
        os.rmdir(new_dir)

    @pytest.mark.skip('not ready')
    def test_save_multipart_file_upload(self):
        pass

    @pytest.mark.skip('remove mocking')
    def test_find_file_path_no_plugin(self, loop, mocker, file_svc):
        data_svc = mocker.Mock()
        data_svc.locate = AsyncMock(return_value=[])
        mocker.patch.object(file_svc, 'data_svc', new=data_svc)
        filename = 'unittest-file-path-test'
        path = 'data'
        with open('./%s/%s' % (path, filename), 'w') as f:
            f.write('test')

        _, file_path = loop.run_until_complete(file_svc.find_file_path(filename))
        assert file_path == '%s/%s' % (path, filename)

        # delete file
        os.remove('./%s/%s' % (path, filename))

    @pytest.mark.skip('remove mocking')
    def test_read_file_nonexistent_file(self, loop, mocker, file_svc):
        mocker.patch.object(file_svc, 'find_file_path', new_callable=AsyncMock, return_value=(None, None))
        with pytest.raises(FileNotFoundError):
            loop.run_until_complete(file_svc.read_file('non-existent-file-for-testing'))

    @pytest.mark.skip('remove mocking')
    def test_find_file_path_plugin(self, loop, mocker, demo_plugin, tmpdir, file_svc):
        def walk_file_path_mock(path, name):
            if 'data' in path:
                return path

        plugin = demo_plugin(enabled=True)
        location = 'path/to/file'
        data_svc = mocker.Mock()
        data_svc.locate = AsyncMock(return_value=[plugin])
        mocker.patch.object(file_svc, 'data_svc', new=data_svc)
        mocker.patch.object(file_svc, 'walk_file_path', new_callable=AsyncMock, side_effect=walk_file_path_mock)

        plugin_name, file_path = loop.run_until_complete(file_svc.find_file_path('testfile', location=location))
        print(plugin_name, file_path)
        assert plugin_name == plugin.name
        assert file_path == os.path.join('plugins', plugin.name, 'data', location)

    @pytest.mark.skip('remove mocking')
    def test_read_file_noxor(self, loop, mocker, tmpdir, file_svc):
        plaintext_fn = 'read-file-nonxortest.txt'
        content = b'this is plaintext'
        plaintext_file = tmpdir.join(plaintext_fn)
        plaintext_file.write(content)

        mocker.patch.object(file_svc, 'find_file_path', new_callable=AsyncMock, return_value=(None, str(plaintext_file)))
        name, output = loop.run_until_complete(file_svc.read_file(plaintext_fn))
        assert name == plaintext_fn
        assert output == content

    @pytest.mark.skip('remove mocking')
    def test_read_file_xor(self, loop, mocker, tmpdir, file_svc):
        plaintext_fn = 'xor-plaintext.txt'
        xortext_fn = "%s.xored" % plaintext_fn
        content = b'this is plaintext'
        plaintext_file = tmpdir.join(plaintext_fn)
        plaintext_file.write(content)
        xored_file = tmpdir.join(xortext_fn)
        xor_file(plaintext_file, xored_file)

        mocker.patch.object(file_svc, 'find_file_path', new_callable=AsyncMock, return_value=(None, str(xored_file)))
        name, nonxored_output = loop.run_until_complete(file_svc.read_file(xortext_fn))
        assert name == xortext_fn
        assert nonxored_output == content

    def test_read_write_result_file(self, tmpdir, file_svc):
        link_id = '12345'
        output = 'output testing unit'
        # write output data
        file_svc.write_result_file(link_id=link_id, output=output, location=tmpdir)

        # read output data
        output_data = file_svc.read_result_file(link_id=link_id, location=tmpdir)
        assert output_data == output

    @pytest.mark.skip('remove mocking')
    def test_add_special_payload(self, loop, mocker, file_svc):
        mocker.patch.dict(file_svc.special_payloads)
        payload_name = 'unittest12345'
        payload_func = AsyncMock
        loop.run_until_complete(file_svc.add_special_payload(payload_name, payload_func))

        assert file_svc.special_payloads[payload_name] == payload_func
