import logging
import socket
from unittest import mock
import time

from app.utility.base_world import BaseWorld
from app.contacts.contact_tcp import TcpSessionHandler
from app.contacts.contact_tcp import Contact

logger = logging.getLogger(__name__)


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


class TestContact:

    def test_tcp_contact(self, event_loop, app_svc):
        BaseWorld.set_config('main', 'app.contact.tcp', '127.0.0.1:57012')
        self.services = app_svc.get_services()
        tcp_c2 = Contact(services=self.services)
        tcp_c2.tcp_handler.sessions = [
            mock.Mock(),
            mock.Mock(),
            mock.Mock()
        ]
        event_loop.run_until_complete(tcp_c2.start())
        tcp_c2.tcp_handler.accept = mock.AsyncMock()
        tcp_c2.tcp_handler.send = mock.AsyncMock(return_value=(200, None, b'response', time.time()))
        tcp_c2.contact_svc.handle_heartbeat = mock.AsyncMock(return_value=(None, []))
        tcp_c2.tcp_handler.refresh = mock.AsyncMock()
        tcp_c2.operation_loop = mock.AsyncMock()
        tcp_c2.tcp_handler._attempt_connection = mock.AsyncMock()
        event_loop.run_until_complete(tcp_c2.start())
        assert tcp_c2 is not None

    def test_tcp_contact_errors(self, event_loop, app_svc):
        BaseWorld.set_config('main', 'app.contact.tcp', '127.0.0.1:57012')
        self.services = app_svc.get_services()
        tcp_c2 = Contact(services=self.services)
        session_with_socket_error = mock.Mock()
        session_with_socket_error.write_bytes.side_effect = socket.error()
        tcp_c2.tcp_handler.sessions = [
            session_with_socket_error,
            session_with_socket_error,
            mock.Mock()
        ]
        event_loop.run_until_complete(tcp_c2.start())
        assert tcp_c2 is not None
