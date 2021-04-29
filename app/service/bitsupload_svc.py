import os

from aiohttp.web_exceptions import HTTPOk, HTTPForbidden, HTTPUnauthorized, HTTPConflict
from enum import Enum

from app.utility.base_service import BaseService


class BitsUploadService(BaseService):
    BG_ERROR_CONTEXT_REMOTE_FILE = hex(0x5)
    # official error codes
    BG_E_TOO_LARGE = hex(0x80200020)
    E_INVALIDARG = hex(0x80070057)
    E_ACCESSDENIED = hex(0x80070005)
    ZERO = hex(0x0)  # protocol specification does not give a name for this HRESULT
    # custom error code
    ERROR_CODE_GENERIC = hex(0x1)

    def __init__(self):
        self.log = self.add_service('bitsupload_svc', self)
        self.active_sessions = dict()  # Maps session ID to BITSUploadSession object


class BITSUploadSession(object):
    def __init__(self, session_id, paw, filename, fragment_size_limit):
        self.session_id = session_id
        self.requesting_paw = paw
        self.filename = filename
        self.fragment_size_limit = fragment_size_limit
        self.fragments = []
        self.expected_file_length = -1
        self._status_code = HTTPOk

    def combine_data(self):
        return ''.join([frg['data'] for frg in self.fragments])

    @property
    def status_code(self):
        return self._status_code

    def add_fragment(self, file_total_length, range_start, range_end, data):
        if self.fragment_size_limit < range_end - range_start:
            raise FragmentTooLarge(range_end - range_start)

class BITSProtocolHeaderKeys(Enum):
    SESSION_ID = 'BITS-Session-Id'
    ERROR_CONTEXT = 'BITS-Error-Context'
    ERROR_CODE = 'BITS-Error-Code'
    PACKET_TYPE = 'BITS-Packet-Type'
    SUPPORTED_PROTOCOLS = 'BITS-Supported-Protocols'
    PROTOCOL = 'BITS-Protocol'


class BITSProtocolHeaderValues(Enum):
    ACK = 'Ack'


class BITSHResult(Enum):
    # Default Context
    BG_ERROR_CONTEXT_REMOTE_FILE = hex(0x5)

    # Official error codes
    BG_E_TOO_LARGE = hex(0x80200020)
    E_INVALIDARG = hex(0x80070057)
    E_ACCESSDENIED = hex(0x80070005)
    ZERO = hex(0x0)  # protocol specification does not give a name for this HRESULT

    # Custom error code
    ERROR_CODE_GENERIC = hex(0x1)


class HTTPProtocolHeaderKeys(Enum):
    ACCEPT_ENCODING = 'Accept-Encoding'
    CONTENT_NAME = 'Content-Name'
    CONTENT_LENGTH = 'Content-Length'
    CONTENT_RANGE = 'Content-Range'
    CONTENT_ENCODING = 'Content-Encoding'


class FragmentTooLarge(Exception):
    def __init__(self, fragment_size):
        super().__init__("Oversized fragment received on server")
        self.fragment_size = fragment_size