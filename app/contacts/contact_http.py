import json

from aiohttp import web

from app.utility.base_world import BaseWorld


class Contact(BaseWorld):

    def __init__(self, services):
        self.name = 'http'
        self.description = 'Accept beacons through a REST API endpoint'
        self.app_svc = services.get('app_svc')
        self.contact_svc = services.get('contact_svc')
        self.log = self.create_logger('contact_http')

    async def start(self):
        self.app_svc.application.router.add_route('POST', '/beacon', self._beacon)

    async def _beacon(self, request):
        try:
            profile = json.loads(self.contact_svc.decode_bytes(await request.read()))
            profile['paw'] = profile.get('paw')
            profile['contact'] = profile.get('contact', self.name)
            agent, instructions = await self.contact_svc.handle_heartbeat(**profile)
            response = dict(paw=agent.paw,
                            sleep=await agent.calculate_sleep(),
                            watchdog=agent.watchdog,
                            instructions=json.dumps([json.dumps(i.display) for i in instructions]))
            if agent.pending_contact != agent.contact:
                response['new_contact'] = agent.pending_contact
                self.log.debug('Sending agent instructions to switch from C2 channel %s to %s' % (agent.contact, agent.pending_contact))
            if agent.executor_change_to_assign:
                response['executor_change'] = agent.assign_pending_executor_change()
                self.log.debug('Asking agent to update executor: %s', response.get('executor_change'))
            return web.Response(text=self.contact_svc.encode_string(json.dumps(response)))
        except Exception as e:
            self.log.error('Malformed beacon: %s' % e)
