import logging
import socket
from unittest import mock

from app.contacts.contact_tcp import TcpSessionHandler

logger = logging.getLogger(__name__)


class TestTcpSessionHandler:

    def test_refresh_with_socket_errors(self, loop):
        handler = TcpSessionHandler(services=None, log=logger)

        session_with_socket_error = mock.Mock()
        session_with_socket_error.connection.send.side_effect = socket.error()

        handler.sessions = [
            session_with_socket_error,
            session_with_socket_error,
            mock.Mock()
        ]

        loop.run_until_complete(handler.refresh())
        assert len(handler.sessions) == 1
        assert all(x is not session_with_socket_error for x in handler.sessions)

    def test_refresh_without_socket_errors(self, loop):
        handler = TcpSessionHandler(services=None, log=logger)
        handler.sessions = [
            mock.Mock(),
            mock.Mock(),
            mock.Mock()
        ]

        loop.run_until_complete(handler.refresh())
        assert len(handler.sessions) == 3
