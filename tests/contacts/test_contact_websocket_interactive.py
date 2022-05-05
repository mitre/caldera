import logging
from unittest.mock import MagicMock
from app.contacts.contact_websocket_interactive import Handler
logger = logging.getLogger(__name__)


class TestWebsocketInteractiveHandler:

    async def test_mock_connect(self):
        m = MagicMock()
        handle = Handler(services=m)
        assert handle.name == "WebsocketInteractive"
