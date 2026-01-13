import logging
import socket
from unittest import mock

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

    def test_tcp_contact(self, event_loop):
        tcp_c2 = Contact(services=None)
        tcp_c2.set_up_server = mock.Mock()
        event_loop.run_until_complete(tcp_c2.start())
        assert tcp_c2 is not None
        # ensure background tasks are stopped to avoid pending-task warnings
        if hasattr(tcp_c2, "stop"):
            event_loop.run_until_complete(tcp_c2.stop())
        elif hasattr(tcp_c2, "shutdown"):
            event_loop.run_until_complete(tcp_c2.shutdown())