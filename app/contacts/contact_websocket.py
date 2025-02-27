import asyncio
import websockets

from app.utility.base_world import BaseWorld


class Contact(BaseWorld):
    """
    A class that handles receiving data through web sockets.
    """

    def __init__(self, services):
        self.name = 'websocket'
        self.description = 'Accept data through web sockets'
        self.log = self.create_logger('contact_websocket')
        self.log.level = 100
        self.handler = Handler(services)
        self.stop_future = asyncio.Future()

    async def start(self):
        websocket_config = self.get_config('app.contact.websocket')
        try:
            host, port_str = websocket_config.split(':')
            port = int(port_str)  # Convert port to integer during validation
            
            if not (1 <= port <= 65535):
                raise ValueError("Port number must be between 1 and 65535.")
        
        except ValueError as e:
            self.log.error(f"Invalid websocket config format or port: {websocket_config} - Error: {e}")
            return

        try:
            async with websockets.serve(self.handler.handle, host, port, logger=self.log):
                await self.stop_future
        except OSError as e:
            self.log.error(f"WebSocket error: {e}")

    async def stop(self):
        self.stop_future.set_result('')


class Handler:
    """
    A handler class to process incoming websocket connections.
    """

    def __init__(self, services):
        self.services = services
        self.handles = []
        self.log = BaseWorld.create_logger('websocket_handler')

    async def handle(self, connection):
        try:
            path = connection.request.path
            parts = path.split('/', 1)
            if len(parts) < 2:
                self.log.error(f"Invalid path format: {path}")
                return

            tag_part = parts[1]
            for handle in [h for h in self.handles if tag_part.startswith(h.tag)]:
                await handle.run(connection, path, self.services)
        except Exception as e:
            self.log.error(f"Handler error: {e}", exc_info=True)
