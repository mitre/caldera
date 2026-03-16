import pytest
from app.contacts.contact_dns import Handler


class TestDnsTxtSanitize:
    def test_strips_null_bytes(self):
        data = b'hello\x00world'
        result = Handler.sanitize_txt_content(data)
        assert result == b'helloworld'

    def test_enforces_max_size(self):
        data = b'A' * 100000
        result = Handler.sanitize_txt_content(data)
        assert len(result) == Handler.MAX_TXT_CONTENT_SIZE

    def test_empty_data_passthrough(self):
        assert Handler.sanitize_txt_content(b'') == b''

    def test_none_data_passthrough(self):
        assert Handler.sanitize_txt_content(None) is None

    def test_normal_data_unchanged(self):
        data = b'{"paw": "test123", "contact": "dns"}'
        result = Handler.sanitize_txt_content(data)
        assert result == data

    def test_multiple_null_bytes_stripped(self):
        data = b'\x00\x00hello\x00\x00world\x00\x00'
        result = Handler.sanitize_txt_content(data)
        assert result == b'helloworld'
