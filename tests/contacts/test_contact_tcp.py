import logging
import socket
from unittest import mock

from app.contacts.contact_tcp import TcpSessionHandler

logger = logging.getLogger(__name__)


class TestTcpSessionHandler:

    def test_refresh_with_socket_errors(self, event_loop, async_return):
        handler = TcpSessionHandler(services=None, log=logger)

        session_with_socket_error = mock.Mock()
        session_with_socket_error.connection.send.side_effect = socket.error()

        standard_session = mock.Mock()
        standard_session.connection.send.return_value = async_return(True)

        handler.sessions = [
            session_with_socket_error,
            session_with_socket_error,
            standard_session
        ]

        event_loop.run_until_complete(handler.refresh())
        assert len(handler.sessions) == 1
        assert all(x is not session_with_socket_error for x in handler.sessions)

    def test_refresh_without_socket_errors(self, event_loop, async_return):
        standard_session = mock.Mock()
        standard_session.connection.send.return_value = async_return(True)

        handler = TcpSessionHandler(services=None, log=logger)
        handler.sessions = [
            standard_session,
            standard_session,
            standard_session
        ]

        event_loop.run_until_complete(handler.refresh())
        assert len(handler.sessions) == 3
