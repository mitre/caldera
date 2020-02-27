import json
import socket
import asyncio
import logging


class Handle:

    def __init__(self, tag, services):
        self.tag = tag
        self.services = services
        self.history = []
        self.log = logging.getLogger('chat_handler')

    async def run(self, sock, path, users):
        async def _chat(mes, mes_obj):
            self.history.append(mes)
            await send_all(mes)

        async def _init(mes, mes_obj):
            self.log.debug(f'got init message: {mes}')
            if len(self.history) > 0:
                hist = {'type': 'history',
                        'data': self.history
                        }
                await sock.send(json.dumps(hist))

        async def _server_init(mes, mes_obj):
            self.log.debug(f'got init message: {mes}')
            if len(self.history) > 0:
                await asyncio.wait([sock.send(old_message) for old_message in self.history])
            if mes_obj['data']['host'] != socket.gethostname():
                config = self.services.get('contact_svc').get_config()
                config['teammates'][mes_obj['user']] = mes_obj['data']['ip']
            websocket_contact = {c.name: c for c in self.services.get('contact_svc').contacts}['websocket']
            websocket_contact.start_client(mes_obj['data']['ip'], '7012', path)

        async def send_all(mes):
            if len(users) > 1:
                await asyncio.wait([ws.send(mes) for ws in users if sock != ws])

        message_handlers = {
            'chat': _chat,
            'init': _init,
            'server_init': _server_init
        }

        while True:
            message = await sock.recv()
            try:
                m = json.loads(message)
                await message_handlers[m['type']](message, m)
            except Exception as e:
                self.log.debug(f'exception on message processing: {message}, exception:{repr(e)}')
