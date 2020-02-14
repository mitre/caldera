import asyncio
import json

from app.contacts.handlers.handlers import Handler
from app.utility.base_world import BaseWorld


class Udp(BaseWorld):

    def __init__(self, services):
        self.name = 'stream'
        self.description = 'Accept streaming messages via UDP'
        self.log = self.create_logger('contact_udp')
        self.contact_svc = services.get('contact_svc')
        self.udp_handler = UdpSessionHandler(services)

    async def start(self):
        loop = asyncio.get_event_loop()
        udp = self.get_config('app.contact.udp')
        loop.create_task(loop.create_datagram_endpoint(lambda: self.udp_handler, local_addr=('0.0.0.0', udp.split(':')[1])))

    @staticmethod
    def valid_config():
        return True


class UdpSessionHandler(asyncio.DatagramProtocol):

    def __init__(self, services):
        super().__init__()
        self.services = services
        self.log = BaseWorld.create_logger('udp_session')

    def datagram_received(self, data, addr):
        async def handle_msg():
            try:
                message = json.loads(data.decode())
                await Handler(message.pop('tag')).handle(message, self.services, addr[0])
            except Exception as e:
                self.log.debug(e)
        asyncio.get_event_loop().create_task(handle_msg())
