import uuid

from aiohttp import web
from enum import Enum

from app.utility.base_service import BaseService


class BitsUploadService(BaseService):
    PROTOCOL_VERSION = "HTTP/1.1"
    # The only existing protocol version to date
    SUPPORTED_BITS_PROTOCOLS = {"{7df0354d-249b-430f-820d-3d2a9bef4931}"}
    FRAGMENT_SIZE_LIMIT = 100 * 1024 * 1024

    def __init__(self):
        self.log = self.add_service('bitsupload_svc', self)
        self.active_sessions = dict()  # Maps session ID to BITSUploadSession object
        self._handlers = {
            'create-session': self.handle_create_session,
            'close-session': self.handle_close_session,
            'cancel-session': self.handle_cancel_session,
            'ping': self.handle_ping,
            'fragment': self.handle_fragment,
        }

    async def handle_bits_post(self, request):
        bits_packet_type = request.headers.get(BITSProtocolHeaderKeys.PACKET_TYPE.value, '').lower()
        handler_func = self._handlers.get(bits_packet_type)
        error_headers = dict()
        if handler_func:
            try:
                self.log.debug('Handling request for %s', bits_packet_type)
                return await handler_func(request)
            except web.HTTPOk as http_ok:
                raise http_ok
            except Exception as e:
                self.log.error('Exception when running handler func for %s: %s', bits_packet_type, e)
                error_headers[BITSProtocolHeaderKeys.ERROR_CODE.value] = BITSHResult.ERROR_CODE_GENERIC.value
                error_headers[
                    BITSProtocolHeaderKeys.ERROR_CONTEXT.value] = BITSHResult.BG_ERROR_CONTEXT_REMOTE_FILE.value
                self.log.error('Internal BITS Upload Service Error. context: %s, code: %s',
                               error_headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value],
                               error_headers[BITSProtocolHeaderKeys.ERROR_CODE.value])
                return web.HTTPInternalServerError(headers=error_headers)
        else:
            error_headers[BITSProtocolHeaderKeys.ERROR_CODE.value] = BITSHResult.E_INVALIDARG.value
            error_headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value] = BITSHResult.BG_ERROR_CONTEXT_REMOTE_FILE.value
            self.log.error('Internal BITS Upload Service Error. context: %s, code: %s',
                           error_headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value],
                           error_headers[BITSProtocolHeaderKeys.ERROR_CODE.value])
            return web.HTTPBadRequest(headers=error_headers)

    async def handle_create_session(self, request):
        """Handles Create-Session packet from client. Creates the UploadSession.
        The unique ID that identifies a session in this server is a randomly generated UUID."""
        self.log.debug('Handling create session')
        headers = {
            BITSProtocolHeaderKeys.PACKET_TYPE.value: BITSProtocolHeaderValues.ACK.value,
            HTTPProtocolHeaderKeys.CONTENT_LENGTH.value: '0'
        }
        supported_protocol_versions = self._get_supported_protocol_versions(request)
        if supported_protocol_versions:
            headers[BITSProtocolHeaderKeys.PROTOCOL.value] = next(iter(supported_protocol_versions))
            dest_dir = self._generate_unique_id()
            session_id = self._generate_unique_id()
            self.log.debug("Creating BITS-Session-Id %s with dest dir %s", session_id, dest_dir)
            self.active_sessions[session_id] = BITSUploadSession(session_id, dest_dir, self.FRAGMENT_SIZE_LIMIT)
            headers[BITSProtocolHeaderKeys.SESSION_ID.value] = session_id
            headers[HTTPProtocolHeaderKeys.ACCEPT_ENCODING.value] = 'identity'
            return web.Response(headers=headers)
        else:
            return self._handle_unsupported_protocol_version(headers)

    async def handle_close_session(self, request):
        self.log.debug('Handling close session')
        return self._release_resources(request)

    async def handle_cancel_session(self, request):
        self.log.debug('Handling cancel session')
        return self._release_resources(request)

    async def handle_ping(self, _):
        self.log.debug('Handling ping')
        return web.Response(headers={
            BITSProtocolHeaderKeys.PACKET_TYPE.value: BITSProtocolHeaderValues.ACK.value,
            # BITSProtocolHeaderKeys.ERROR_CODE.value: '1',
            # BITSProtocolHeaderKeys.ERROR_CONTEXT.value: '',
            HTTPProtocolHeaderKeys.CONTENT_LENGTH.value: '0'
        })

    async def handle_fragment(self, request):
        """Handles a new Fragment packet from the client, adding it to the relevant upload session."""
        headers = {
            BITSProtocolHeaderKeys.PACKET_TYPE.value: BITSProtocolHeaderValues.ACK.value,
            HTTPProtocolHeaderKeys.CONTENT_LENGTH.value: '0'
        }
        session_id = request.headers.get(BITSProtocolHeaderKeys.SESSION_ID.value, '').lower()
        if session_id:
            self.log.debug('Handling fragment for session %s', session_id)
            length_val, name, _, range_val = self._get_fragment_request_headers(request)
            if not name:
                name = "testing"  # later change to filepath thing
            if length_val and range_val:
                content_range = range_val.split(' ')[-1]
                headers[BITSProtocolHeaderKeys.SESSION_ID.value] = session_id
                crange, total_length_str = content_range.split("/")
                total_length = int(total_length_str)
                range_start, range_end = [int(num) for num in crange.split("-")]
                data = await request.content.read()
                session = self.active_sessions.get(session_id)
                if session:
                    try:
                        is_last_fragment = session.add_fragment(total_length, range_start, range_end, data)
                    except InvalidFragment as e:
                        return self._handle_invalid_fragment_exception(session_id, headers, e)
                    except FragmentTooLarge as e:
                        return self._handle_fragment_too_large_exception(session_id, headers, e)

                    if is_last_fragment:
                        self.log.debug('Received last fragment. Writing uploaded data.')
                        await self._write_uploaded_data(session, name)
                    headers[BITSProtocolHeaderKeys.RECEIVED_CONTENT_RANGE.value] = str(range_end + 1)
                    self.log.debug('Process fragment bytes %d:%d', range_start, range_end)
                    return web.Response(headers=headers)
                else:
                    self.log.error('Session not found for ID %s', session_id)
                    headers[BITSProtocolHeaderKeys.ERROR_CODE.value] = BITSHResult.ERROR_CODE_GENERIC.value
                    headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value] = \
                        BITSHResult.BG_ERROR_CONTEXT_REMOTE_FILE.value
                    return web.HTTPInternalServerError(headers=headers)
            else:
                self.log.error('Missing length or range')
                headers[BITSProtocolHeaderKeys.ERROR_CODE.value] = BITSHResult.ERROR_CODE_GENERIC.value
                headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value] = BITSHResult.BG_ERROR_CONTEXT_REMOTE_FILE.value
                return web.HTTPBadRequest(headers=headers)
        else:
            return self._handle_missing_session_id(headers)

    async def _write_uploaded_data(self, session, filename):
        file_svc = self.get_service('file_svc')
        if file_svc:
            data = session.combine_data()
            dest_dir_path = await file_svc.create_exfil_sub_directory(session.dest_dir)
            await file_svc.save_file(filename, data, dest_dir_path, encrypt=False)
        else:
            raise Exception('File service not available.')

    def _handle_invalid_fragment_exception(self, session_id, headers, exception):
        headers[BITSProtocolHeaderKeys.ERROR_CODE.value] = BITSHResult.ZERO.value
        headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value] = BITSHResult.BG_ERROR_CONTEXT_REMOTE_FILE.value
        self.log.error('ERROR processing new fragment (BITS-Session-Id: %s): ' +
                       'New fragment range (%d) is not contiguous with last received (%d).' +
                       'context:%s, code:%s, exception:%s', session_id, exception.new_range_start,
                       exception.last_range_end, headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value],
                       headers[BITSProtocolHeaderKeys.ERROR_CODE.value], repr(exception))
        return web.HTTPRequestRangeNotSatisfiable(headers=headers)

    def _handle_fragment_too_large_exception(self, session_id, headers, exception):
        headers[BITSProtocolHeaderKeys.ERROR_CODE.value] = BITSHResult.BG_E_TOO_LARGE.value
        headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value] = BITSHResult.BG_ERROR_CONTEXT_REMOTE_FILE.value
        self.log.error('ERROR processing new fragment (BITS-Session-Id: %s): ' +
                       'New fragment size (%d) exceeds server limit (%d).' +
                       'context:%s, code:%s, exception:%s', session_id, exception.fragment_size,
                       self.FRAGMENT_SIZE_LIMIT, headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value],
                       headers[BITSProtocolHeaderKeys.ERROR_CODE.value], repr(exception))
        return web.HTTPInternalServerError(headers=headers)

    def _release_resources(self, request):
        """Releases server resources for a session termination caused by either Close-Session or Cancel-Session."""
        headers = {
            BITSProtocolHeaderKeys.PACKET_TYPE.value: BITSProtocolHeaderValues.ACK.value,
            HTTPProtocolHeaderKeys.CONTENT_LENGTH.value: '0'
        }
        session_id = request.headers.get(BITSProtocolHeaderKeys.SESSION_ID.value, '').lower()
        if session_id:
            if not self.active_sessions.pop(session_id):
                # Session was not found
                self.log.error('No session found for id %s', session_id)
                headers[BITSProtocolHeaderKeys.ERROR_CODE.value] = BITSHResult.BG_E_SESSION_NOT_FOUND.value
                headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value] = BITSHResult.BG_ERROR_CONTEXT_REMOTE_FILE.value
                return web.HTTPBadRequest(headers=headers)
            self.log.debug("Releasing resources for BITS-Session-Id: %s", session_id)
            return web.Response(headers=headers)
        else:
            return self._handle_missing_session_id(headers)

    def _get_supported_protocol_versions(self, request):
        client_supported_protocols = \
            request.headers.get(BITSProtocolHeaderKeys.SUPPORTED_PROTOCOLS.value, '').lower().split(' ')
        return set(client_supported_protocols).intersection(self.SUPPORTED_BITS_PROTOCOLS)

    def _handle_unsupported_protocol_version(self, headers):
        self.log.error('Error creating new session - protocol mismatch.')
        headers[BITSProtocolHeaderKeys.ERROR_CODE.value] = BITSHResult.E_INVALIDARG.value
        headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value] = BITSHResult.BG_ERROR_CONTEXT_REMOTE_FILE.value
        return web.HTTPBadRequest(headers=headers)

    def _handle_missing_request_id(self, headers):
        self.log.error('No request ID provided via X-Request-ID header.')
        headers[BITSProtocolHeaderKeys.ERROR_CODE.value] = BITSHResult.E_INVALIDARG.value
        headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value] = BITSHResult.BG_ERROR_CONTEXT_REMOTE_FILE.value
        return web.HTTPBadRequest(headers=headers)

    def _handle_missing_session_id(self, headers):
        self.log.error('No BITS session ID provided.')
        headers[BITSProtocolHeaderKeys.ERROR_CODE.value] = BITSHResult.E_INVALIDARG.value
        headers[BITSProtocolHeaderKeys.ERROR_CONTEXT.value] = BITSHResult.BG_ERROR_CONTEXT_REMOTE_FILE.value
        return web.HTTPBadRequest(headers=headers)

    @staticmethod
    def _generate_unique_id():
        return str(uuid.uuid4())

    @staticmethod
    def _get_fragment_request_headers(request):
        content_length_val = request.headers.get(HTTPProtocolHeaderKeys.CONTENT_LENGTH.value)
        content_name = request.headers.get(HTTPProtocolHeaderKeys.CONTENT_NAME.value)
        content_encoding = request.headers.get(HTTPProtocolHeaderKeys.CONTENT_ENCODING.value)
        content_range_val = request.headers.get(HTTPProtocolHeaderKeys.CONTENT_RANGE.value)
        return content_length_val, content_name, content_encoding, content_range_val


class BITSUploadSession(object):
    def __init__(self, session_id, dest_dir, fragment_size_limit):
        self.session_id = session_id
        self.dest_dir = dest_dir
        self.fragment_size_limit = fragment_size_limit
        self.fragments = []  # List of dicts
        self.expected_file_length = -1

    def combine_data(self):
        return b''.join([frg.get('data', b'') for frg in self.fragments])

    def add_fragment(self, file_total_length, range_start, range_end, data):
        """Applies new fragment received from client to the upload session.
        Returns True if fragment is the last one in the session, False otherwise.
        """
        if self.fragment_size_limit < range_end - range_start:
            raise FragmentTooLarge(range_end - range_start)
        if self.expected_file_length == -1:
            self.expected_file_length = file_total_length
        last_range_end = self.fragments[-1]['range_end'] if self.fragments else -1
        if last_range_end + 1 < range_start:
            # New fragment's range is not contiguous with the previous fragment
            raise InvalidFragment(last_range_end, range_start)
        elif last_range_end + 1 > range_start:
            # New fragment partially overlaps last fragment
            # BITS protocol states that server should treat only the non-overlapping part
            range_start = last_range_end + 1
        self.fragments.append(dict(range_start=range_start,
                                   range_end=range_end,
                                   data=data))
        return range_end + 1 == self.expected_file_length


class BITSProtocolHeaderKeys(Enum):
    SESSION_ID = 'BITS-Session-Id'
    ERROR_CONTEXT = 'BITS-Error-Context'
    ERROR_CODE = 'BITS-Error-Code'
    PACKET_TYPE = 'BITS-Packet-Type'
    SUPPORTED_PROTOCOLS = 'BITS-Supported-Protocols'
    PROTOCOL = 'BITS-Protocol'
    RECEIVED_CONTENT_RANGE = 'BITS-Received-Content-Range'


class BITSProtocolHeaderValues(Enum):
    ACK = 'Ack'


class BITSHResult(Enum):
    # Default Context
    BG_ERROR_CONTEXT_REMOTE_FILE = hex(0x5)

    # Official error codes
    BG_E_TOO_LARGE = hex(0x80200020)
    BG_E_SESSION_NOT_FOUND = hex(0x8020001F)
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


class InvalidFragment(Exception):
    def __init__(self, last_range_end, new_range_start):
        super().__init__("Invalid fragment received on server")
        self.last_range_end = last_range_end
        self.new_range_start = new_range_start
