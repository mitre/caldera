import os
import pytest


class MockDataService:

    @staticmethod
    async def locate(*args, **kwargs):
        return []


@pytest.mark.usefixtures(
    'init_base_world'
)
class TestFileService:

    def test_save_get_file(self, loop, file_svc):
        filename = 'unittest-file-save-test'
        content = b'content!'
        path = 'data'

        # create and save a file
        file_svc.data_svc = MockDataService()
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

    @pytest.mark.skip('not ready')
    def test_find_file_path(self):
        pass

    @pytest.mark.skip('not ready')
    def test_read_file(self):
        pass

    @pytest.mark.skip('not ready')
    def test_read_result_file(self):
        pass

    @pytest.mark.skip('not ready')
    def test_write_result_file(self):
        pass

    @pytest.mark.skip('not ready')
    def test_add_special_payload(self):
        pass

    @pytest.mark.skip('not ready')
    def test_compile_go(self):
        pass
