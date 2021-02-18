import logging
import socket
from unittest import mock
from unittest import IsolatedAsyncioTestCase

from app.contacts.contact_tcp import TcpSessionHandler

logger = logging.getLogger(__name__)


class TestTcpSessionHandler(IsolatedAsyncioTestCase):

    async def test_refresh_with_socket_errors(self):
        handler = TcpSessionHandler(services=None, log=logger)

        session_with_socket_error = mock.Mock()
        session_with_socket_error.connection.send.side_effect = socket.error()

        handler.sessions = [
            session_with_socket_error,
            session_with_socket_error,
            mock.Mock()
        ]

        await handler.refresh()
        assert len(handler.sessions) == 1
        assert all(x is not session_with_socket_error for x in handler.sessions)

    async def test_refresh_without_socket_errors(self):
        handler = TcpSessionHandler(services=None, log=logger)
        handler.sessions = [
            mock.Mock(),
            mock.Mock(),
            mock.Mock()
        ]

        await handler.refresh()
        assert len(handler.sessions) == 3
