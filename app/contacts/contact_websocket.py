import asyncio
import json
import websockets

from datetime import datetime

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
            session_id = path.split('/')[2]
            cmd = await socket.recv()
            handler = self.services.get('term_svc').socket_conn.tcp_handler
            paw = next(i.paw for i in handler.sessions if i.id == int(session_id))
            self.services.get('term_svc').reverse_report[paw].append(
                dict(date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cmd=cmd)
            )
            status, pwd, reply = await handler.send(session_id, cmd)
            await socket.send(json.dumps(dict(response=reply.strip(), pwd=pwd)))
        except Exception as e:
            self.log.debug(e)
