"""Verify that V1 file endpoints now have @check_authorization decorator."""
import inspect
from app.api.rest_api import RestApi


class TestV1FileEndpointAuth:
    def test_upload_file_has_auth_wrapper(self):
        # check_authorization wraps functions in a 'helper' closure
        source = inspect.getsource(RestApi.upload_file)
        assert 'check_authorization' in source or 'auth_svc' in source

    def test_download_file_has_auth_wrapper(self):
        source = inspect.getsource(RestApi.download_file)
        assert 'check_authorization' in source or 'auth_svc' in source
