import websockets

from app.utility.base_world import BaseWorld


class WebSocket(BaseWorld):

    def __init__(self, services):
        self.name = 'websocket'
        self.description = 'Accept data through web sockets'
        self.log = self.create_logger('contact_websocket')
        self.handler = Handler(services)

    async def start(self):
        web_socket = self.get_config('app.contact.websocket')
        await websockets.serve(self.handler.handle, '0.0.0.0', web_socket.split(':')[1])


class Handler:

    def __init__(self, services):
        self.services = services
        self.handles = []
        self.log = BaseWorld.create_logger('websocket_handler')

    async def handle(self, socket, path):
        try:
            for handle in [h for h in self.handles if h.tag == path.split('/')[1]]:
                await handle.run(socket, path, self.services)
        except Exception as e:
            self.log.debug(e)
