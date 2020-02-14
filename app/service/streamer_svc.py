import asyncio
import json

from app.utility.base_service import BaseService
from app.utility.base_world import BaseWorld
from app.utility.handlers import Handler


class StreamerService(BaseService):

    def __init__(self):
        self.log = self.add_service('streamer_svc', self)
        self.udp_handler = None

    def turn_on(self):
        self.log.debug('Turning on streamer socket')
        loop = asyncio.get_event_loop()
        self.udp_handler = UdpSessionHandler()
        loop.create_task(loop.create_datagram_endpoint(lambda: self.udp_handler, local_addr=('0.0.0.0', 5999)))

    def turn_off(self):
        self.log.debug('Turning off streamer socket')


class UdpSessionHandler(asyncio.DatagramProtocol):

    def __init__(self):
        super().__init__()
        self.log = BaseWorld.create_logger('stream')

    def datagram_received(self, data, addr):
        async def handle_msg():
            try:
                profile = json.loads(data.decode())
                Handler(profile['type']).handle(data)
            except Exception as e:
                self.log.debug(e)
        asyncio.get_event_loop().create_task(handle_msg())
