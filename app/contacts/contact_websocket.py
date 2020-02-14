import asyncio

import websockets

from app.contacts.handlers.h_websocket import Handler
from app.utility.base_world import BaseWorld


class WebSocket(BaseWorld):

    def __init__(self, services):
        self.name = 'web socket'
        self.description = 'Accept data through web sockets'
        self.log = self.create_logger('contact_websocket')
        self.socket_handler = SocketHandler(services)

    async def start(self):
        loop = asyncio.get_event_loop()
        web_socket = self.get_config('app.contact.websocket')
        loop.create_task(await websockets.serve(self.socket_handler.handle, '0.0.0.0', web_socket.split(':')[1]))

    @staticmethod
    def valid_config():
        return True


class SocketHandler:

    def __init__(self, services):
        self.services = services
        self.log = BaseWorld.create_logger('websocket_session')

    async def handle(self, socket, path):
        try:
            await Handler(path.split('/')[1]).handle(socket, path, self.services)
        except Exception as e:
            self.log.debug(e)
