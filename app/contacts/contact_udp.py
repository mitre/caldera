import asyncio
import json
import socket

from app.utility.base_world import BaseWorld


class Udp(BaseWorld):

    def __init__(self, services):
        self.name = 'udp'
        self.description = 'Communication occurs through a raw UDP socket'
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
        self.log = BaseWorld.create_logger('udp_session')
        self.contact_svc = services.get('contact_svc')

    def datagram_received(self, data, addr):
        async def handle_beacon():
            try:
                # save beacon
                profile = json.loads(data.decode())
                callback = profile.pop('callback', None)
                profile['executors'] = [e for e in profile.get('executors', '').split(',') if e]
                profile['contact'] = 'udp'
                await self.contact_svc.handle_heartbeat(**profile)

                # send confirmation
                if callback:
                    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                    sock.sendto('roger'.encode(), (addr[0], int(callback)))
            except Exception as e:
                self.log.debug(e)
        asyncio.get_event_loop().create_task(handle_beacon())
