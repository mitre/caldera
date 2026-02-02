import logging
import socket
from unittest import mock
import pytest


from app.service.contact_svc import ContactService
from app.utility.base_world import BaseWorld
from app.contacts.contact_tcp import TcpSessionHandler
from app.contacts.contact_tcp import Contact
from app.contacts.utility.c_tcp_session import TCPSession
from app.objects.secondclass.c_instruction import Instruction

logger = logging.getLogger(__name__)


@pytest.fixture
def tcp_c2(app_svc, contact_svc, data_svc, obfuscator):
    services = app_svc.get_services()
    tcp_contact_svc = Contact(services=services)
    return tcp_contact_svc


class _MockReader:
    async def read(self, n=-1):
        return b'MockContent'


class _MockWriter:
    def write(self, data):
        pass


class TestTcpSessionHandler:

    def test_refresh_with_socket_errors(self, event_loop):
        handler = TcpSessionHandler(services=None, log=logger)

        session_with_socket_error = mock.Mock()
        session_with_socket_error.write_bytes.side_effect = socket.error()

        handler.sessions = [
            session_with_socket_error,
            session_with_socket_error,
            mock.Mock()
        ]

        event_loop.run_until_complete(handler.refresh())
        assert len(handler.sessions) == 1
        assert all(x is not session_with_socket_error for x in handler.sessions)

    def test_refresh_without_socket_errors(self, event_loop):
        handler = TcpSessionHandler(services=None, log=logger)
        handler.sessions = [
            mock.Mock(),
            mock.Mock(),
            mock.Mock()
        ]

        event_loop.run_until_complete(handler.refresh())
        assert len(handler.sessions) == 3

    async def test_attempt_connection(self, tcp_c2):
        MockSession = TCPSession(id=123456, paw='testpaw', reader=_MockReader(), writer=_MockWriter())
        assert "MockContent" == await tcp_c2.tcp_handler._attempt_connection(MockSession, timeout=1)


class TestContact:

    def test_tcp_contact(self, event_loop, tcp_c2):
        BaseWorld.set_config('main', 'app.contact.tcp', '127.0.0.1:57012')
        dummy_instruction = Instruction(
            id='123',
            sleep=5,
            command='whoami',
            executor='sh',
            timeout=60,
            payloads=[],
            uploads=[],
            deadman=False,
            delete_payload=True
        )
        tcp_c2.tcp_handler.sessions.append(TCPSession(
            id=1,
            paw='dummy_paw',
            reader=_MockReader(),
            writer=_MockWriter()
        ))
        event_loop.run_until_complete(tcp_c2.start())
        with mock.patch.object(ContactService, 'handle_heartbeat', return_value=('dummy_paw', [dummy_instruction])):
            event_loop.run_until_complete(tcp_c2.handle_sessions())
        assert len(tcp_c2.tcp_handler.sessions) == 1
