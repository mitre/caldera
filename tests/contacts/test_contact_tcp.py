import json
import logging
import socket
from unittest import mock
from tests.conftest import async_return

from app.contacts.contact_tcp import TcpSessionHandler
from plugins.manx.app.c_session import Session

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

    async def test_send_with_connection_errors(self, async_return):
        test_session_id = 123
        test_paw = 'paw123'
        test_cmd = 'whoami'
        test_exception = Exception('Exception Raised')

        mock_connection = mock.Mock()
        mock_connection.send.return_value = async_return(True)
        standard_session = Session(id=test_session_id, paw=test_paw, connection=mock_connection)

        handler = TcpSessionHandler(services=None, log=logger)
        handler.sessions = [
            standard_session,
            standard_session
        ]

        handler._attempt_connection = mock.Mock()
        handler._attempt_connection.side_effect = test_exception
        response = await handler.send(test_session_id, test_cmd)
        expected_response = (1, '~$ ', str(test_exception), '')

        assert len(handler.sessions) == 2
        assert response == expected_response

    async def test_send_without_connection_error(self, async_return):
        test_session_id = 123
        test_paw = 'paw123'
        test_cmd = 'whoami'
        json_response = {
            'status': 0,
            'pwd': '/test',
            'response': ''
        }
        expected_response = (json_response['status'], json_response['pwd'], json_response['response'],
                             json_response.get('agent_reported_time', ''))

        mock_connection = mock.Mock()
        mock_connection.send.return_value = async_return(True)
        standard_session = Session(id=test_session_id, paw=test_paw, connection=mock_connection)

        handler = TcpSessionHandler(services=None, log=logger)
        handler.sessions = [
            standard_session,
            standard_session
        ]

        handler._attempt_connection = mock.Mock()
        handler._attempt_connection.return_value = async_return(json.dumps(json_response))
        received_response = await handler.send(test_session_id, test_cmd)

        assert len(handler.sessions) == 2
        assert received_response == expected_response
