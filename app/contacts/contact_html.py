import json

from aiohttp_jinja2 import template

from app.utility.base_world import BaseWorld


class Contact(BaseWorld):

    def __init__(self, services):
        self.name = 'html'
        self.description = 'Accept beacons through an HTML page'
        self.app_svc = services.get('app_svc')
        self.contact_svc = services.get('contact_svc')
        self.log = self.create_logger('contact_html')

    async def start(self):
        self.app_svc.application.router.add_route('*', self.get_config('app.contact.html'), self._accept_beacon)

    @template('weather.html')
    async def _accept_beacon(self, request):
        default_context = dict(
            instructions=self._encode_response_payload(
                paw='',
                sleep=60,
                watchdog=0,
                instructions=[]
            ),
            contact_path=self.get_config('app.contact.html')
        )
        try:
            body = await request.text()
            if not body:
                return default_context

            profile = json.loads(self.decode_bytes(body))
            profile['paw'] = profile.get('paw')
            profile['contact'] = 'html'
            agent, instructions = await self.contact_svc.handle_heartbeat(**profile)
            return dict(
                instructions=self._encode_response_payload(
                    paw=agent.paw,
                    sleep=await agent.calculate_sleep(),
                    watchdog=agent.watchdog,
                    instructions=[json.dumps(i.display) for i in instructions]
                ),
                contact_path=self.get_config('app.contact.html')
            )
        except Exception as e:
            self.log.error('Malformed HTML beacon: %s', e)
            return default_context

    def _encode_response_payload(self, paw, sleep, watchdog, instructions):
        response = dict(
            paw=paw,
            sleep=sleep,
            watchdog=watchdog,
            instructions=json.dumps(instructions)
        )
        return self.encode_string(json.dumps(response))
