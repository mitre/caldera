from app.utility.base_service import BaseService
import time
import asyncio


class C2Service(BaseService):

    def __init__(self, services):
        self.agent_svc = services.get('agent_svc')
        self.log = self.add_service('c2_svc', self)
        self.running = False
        self.q = asyncio.Queue()
        self.loop = asyncio.get_event_loop()

    async def start_channel(self, c2_channel):
        if c2_channel.c2_type == 'active':
            if not self.running:
                self.loop.create_task(self._handle_c2_channels(self.q))
                self.running = True
            await self.q.put(c2_channel)
        elif c2_channel.c2_type == 'passive':
            # TODO: not yet implemented
            pass

    """ PRIVATE """

    async def _handle_c2_channels(self, queue):
        while True:
            c2 = await queue.get()
            received_data = await c2.get_beacons()
            for beacon in received_data:
                await self.agent_svc.handle_heartbeat(**beacon)
            queue.put(c2)
            time.sleep(10)
