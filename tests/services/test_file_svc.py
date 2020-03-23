import os
import pytest

from tests import AsyncMock


@pytest.mark.usefixtures(
    'init_base_world'
)
class TestFileService:

    @pytest.fixture
    def setup_mock_dataservice(self, mocker):
        pass

    def test_get_file_no_file_header(self, loop, file_svc):
        with pytest.raises(KeyError):
            loop.run_until_complete(file_svc.get_file(headers=dict()))

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

    def test_read_file_nonexistent_file(self, loop, mocker, file_svc):
        mocker.patch.object(file_svc, 'find_file_path', new_callable=AsyncMock, return_value=(None, None))
        with pytest.raises(FileNotFoundError):
            loop.run_until_complete(file_svc.read_file("non-existent-file-for-testing"))

    @pytest.mark.skip('not ready')
    def test_find_file_path_plugin(self, loop, mocker, file_svc):
        data_svc = mocker.Mock()
        data_svc.locate = AsyncMock(return_value=['plugin'])

    @pytest.mark.skip('not ready')
    def test_read_file_noxor(self):
        pass

    @pytest.mark.skip('not ready')
    def test_read_file_xor(self):
        pass

    def test_read_write_result_file(self, tmpdir, file_svc):
        link_id = "12345"
        output = "output testing unit"
        # write output data
        file_svc.write_result_file(link_id=link_id, output=output, location=tmpdir)

        # read output data
        output_data = file_svc.read_result_file(link_id=link_id, location=tmpdir)
        assert output_data == output

    def test_add_special_payload(self, loop, mocker, file_svc):
        mocker.patch.dict(file_svc.special_payloads)
        payload_name = "unittest12345"
        payload_func = AsyncMock
        loop.run_until_complete(file_svc.add_special_payload(payload_name, payload_func))

        assert file_svc.special_payloads[payload_name] == payload_func
