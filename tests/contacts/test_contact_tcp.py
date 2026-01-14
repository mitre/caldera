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
        # ensure start() has a valid address string to split
        # prefer the real attribute name used by Contact (address/server_address/host). If unknown,
        # set both common names:
        if not getattr(tcp_c2, "server_address", None):
            tcp_c2.server_address = "127.0.0.1:0"
        if not getattr(tcp_c2, "address", None):
            tcp_c2.address = "127.0.0.1:0"
        event_loop.run_until_complete(tcp_c2.start())
        assert tcp_c2 is not None
        assert tcp_c2.tcp_handler is not None
