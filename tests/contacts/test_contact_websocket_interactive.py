import logging
import socket
from unittest.mock import AsyncMock, MagicMock
from app.contacts.contact_websocket_interactive import Handler, Contact
from tests.conftest import app_svc
logger = logging.getLogger(__name__)


class TestWebsocketInteractiveHandler:

    async def test_mock_connect(self):
        m = MagicMock()
        handle = Handler(services=m)
        assert handle.name == "WebsocketInteractive"
