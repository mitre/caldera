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

    def setUp(self):
        self.patcher1 = mock.patch('app.contacts.contact_tcp.asyncio.start_server', autospec=True)
        self.patcher2 = mock.patch('app.contacts.contact_tcp.asyncio.get_event_loop', autospec=True)
        self.patcher3 = mock.patch('app.contacts.contact_tcp.BaseWorld.get_config', autospec=True)
        self.patcher4 = mock.patch('app.contacts.contact_tcp.Contact.create_logger', autospec=True)
        self.patcher5 = mock.patch('app.contacts.contact_tcp.Contact.operation_loop', autospec=True)
        self.patcher6 = mock.patch('app.contacts.contact_tcp.Contact.decode_bytes', autospec=True)
        self.patcher7 = mock.patch('app.contacts.contact_tcp.Contact.encode_string', autospec=True)
        self.patcher8 = mock.patch('app.contacts.contact_tcp.Contact.services', autospec=True)
        self.patcher9 = mock.patch('app.contacts.contact_tcp.Contact.contact_svc', autospec=True)
        self.patcher10 = mock.patch('app.contacts.contact_tcp.TcpSessionHandler.send', autospec=True)
        self.patcher11 = mock.patch('app.contacts.contact_tcp.TcpSessionHandler.accept', autospec=True)
        self.patcher12 = mock.patch('app.contacts.contact_tcp.TcpSessionHandler.refresh', autospec=True)
        self.patcher13 = mock.patch('app.contacts.utility.c_tcp_session.TCPSession.write_bytes', autospec=True)
        self.patcher14 = mock.patch('app.contacts.utility.c_tcp_session.TCPSession.read_bytes', autospec=True)
        self.patcher15 = mock.patch('app.contacts.contact_tcp.TcpSessionHandler._handshake', autospec=True)
        self.patcher16 = mock.patch('app.contacts.contact_tcp.TcpSessionHandler._attempt_connection', autospec=True)
        self.patcher1.start()
        self.patcher2.start()
        self.patcher3.start()
        self.patcher4.start()
        self.patcher5.start()
        self.patcher6.start()
        self.patcher7.start()
        self.patcher8.start()
        self.patcher9.start()
        self.patcher10.start()
        self.patcher11.start()
        self.patcher12.start()
        self.patcher13.start()
        self.patcher14.start()
        self.patcher15.start()
        self.patcher16.start()

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
        event_loop.run_until_complete(tcp_c2.tcp_handler.accept(None, None))
        assert tcp_c2 is not None

    def tearDown(self):
        mock.patch.stopall()