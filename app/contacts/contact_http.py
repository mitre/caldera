import json

from aiohttp import web

from app.utility.base_world import BaseWorld


class Http(BaseWorld):

    def __init__(self, services):
        self.name = 'http'
        self.app_svc = services.get('app_svc')
        self.contact_svc = services.get('contact_svc')

    async def start(self):
        self.app_svc.application.router.add_route('POST', '/beacon', self._beacon)
        self.app_svc.application.router.add_route('POST', '/result', self._results)

    @staticmethod
    def valid_config():
        return True

    """ PRIVATE """

    async def _beacon(self, request):
        profile = json.loads(self.contact_svc.decode_bytes(await request.read()))
        profile['paw'] = profile.get('paw')
        profile['contact'] = 'http'
        agent, instructions = await self.contact_svc.handle_heartbeat(**profile)
        response = dict(paw=agent.paw,
                        sleep=await agent.calculate_sleep(),
                        watchdog=agent.watchdog,
                        instructions=json.dumps([json.dumps(i.display) for i in instructions]))
        return web.Response(text=self.contact_svc.encode_string(json.dumps(response)))

    async def _results(self, request):
        data = json.loads(self.contact_svc.decode_bytes(await request.read()))
        await self.contact_svc.save_results(**data)
