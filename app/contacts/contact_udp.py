import asyncio
import json

from app.contacts.handles.h_beacon import Handle
from app.utility.base_world import BaseWorld


class Contact(BaseWorld):

    def __init__(self, services):
        self.name = 'udp'
        self.description = 'Accept streaming messages via UDP'
        self.log = self.create_logger('contact_udp')
        self.contact_svc = services.get('contact_svc')
        self.handler = Handler(services)

    async def start(self):
        loop = asyncio.get_event_loop()
        udp = self.get_config('app.contact.udp')
        addr, port = udp.split(':')
        loop.create_task(loop.create_datagram_endpoint(lambda: self.handler, local_addr=(addr, port)))


class Handler(asyncio.DatagramProtocol):

    def __init__(self, services):
        super().__init__()
        self.services = services
        self.handles = [
            Handle(tag='beacon')
        ]
        self.log = BaseWorld.create_logger('udp_handler')

    def datagram_received(self, data, addr):
        async def handle_msg():
            try:
                message = json.loads(data.decode())
                for handle in [h for h in self.handles if h.tag == message.pop('tag')]:
                    await handle.run(message, self.services, addr[0])
            except Exception as e:
                self.log.debug(e)
        asyncio.get_event_loop().create_task(handle_msg())
