import os
import pytest

from tests import AsyncMock
from asyncio import Future


@pytest.mark.usefixtures(
    'init_base_world'
)
class TestFileService:

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
