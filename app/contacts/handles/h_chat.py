import json
import socket
import asyncio
import logging


class Handle:

    def __init__(self, tag, services):
        self.tag = tag
        self.services = services
        self.history = []
        self.servers = set()
        self.log = logging.getLogger('chat_handler')

    async def run(self, sock, path, users):
        async def _chat(mes, mes_obj):
            self.history.append(mes)
            if sock not in self.servers:
                await send_servers(mes)
            await send_users(mes)

        async def _init(mes, mes_obj):
            self.log.debug(f'new chat client initialized')
            if len(self.history) > 0:
                hist = {'type': 'history',
                        'data': self.history
                        }
                await sock.send(json.dumps(hist))

        async def _flag_server(mes, mes_obj):
            self.servers.add(sock)

        async def _server_init(mes, mes_obj):
            self.log.debug(f'new server connecting: {mes_obj["user"]}:{mes_obj["data"]["ip"]}')
            await _flag_server(None, None)
            if len(self.history) > 0:
                await asyncio.wait([sock.send(old_message) for old_message in self.history])
            if mes_obj['data']['host'] != socket.gethostname():
                config = self.services.get('contact_svc').get_config()
                config['teammates'][mes_obj['user']] = mes_obj['data']['ip']
            websocket_contact = {c.name: c for c in self.services.get('contact_svc').contacts}['websocket']
            await websocket_contact.start_client(mes_obj['data']['ip'], '7012', path)

        async def send_all(mes):
            send_to = [s for s in users if s != sock]
            if len(send_to) > 0:
                await asyncio.wait([ws.send(mes) for ws in send_to])

        async def send_users(mes):
            valid_users = users.difference(self.servers)
            valid_users.discard(sock)
            if len(valid_users) > 0:
                await asyncio.wait([ws.send(mes) for ws in valid_users])

        async def send_servers(mes):
            valid_servers = self.servers.intersection(users)
            valid_servers.discard(sock)
            if len(valid_servers) > 0:
                await asyncio.wait([ws.send(mes) for ws in valid_servers])

        message_handlers = {
            'chat': _chat,
            'init': _init,
            'welcome': _flag_server,
            'server_init': _server_init
        }

        welcome = {'type': 'welcome', 'data': 'thanks for connecting to your friendly local chat server'}
        await sock.send(json.dumps(welcome))
        while True:
            message = await sock.recv()
            try:
                m = json.loads(message)
                await message_handlers[m['type']](message, m)
            except Exception as e:
                self.log.debug(f'exception on message processing: {message}, exception:{repr(e)}')
