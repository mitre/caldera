import json

from datetime import datetime
from aiohttp import web


class VetApiBase:

    def __init__(self, services):
        self.data_svc = services.get('data_svc')
        self.utility_svc = services.get('utility_svc')
        self.log = self.utility_svc.create_logger('vet')

    async def heartbeat(self, request):
        paw = request.headers.get('X-PAW')
        data = json.loads(self.utility_svc.decode_bytes(await request.read()))
        agent = await self._handle_beat(paw, **data)
        agent_details = dict(cat=agent['cat'], start='nohup ./sandcat.go 1>/dev/null 2>/dev/null &', stop='pkill -f sandcat')
        return web.Response(text=self.utility_svc.encode_string(json.dumps(agent_details)))

    async def _handle_beat(self, paw, platform, server, group, cat):
        self.log.debug('Heartbeat (%s)' % paw)
        agent = await self.data_svc.explode_agents(criteria=dict(paw=paw))
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if agent:
            updated = dict(last_seen=now, checks=agent[0]['checks'] + 1, cat=cat)
            await self.data_svc.update('core_agent', 'paw', paw, data=updated)
            return agent[0]
        else:
            queued = dict(last_seen=now, paw=paw, checks=1, platform=platform, server=server, host_group=group,
                          cat='sandcat.go')
            await self.data_svc.create_agent(agent=queued)
            return (await self.data_svc.explode_agents(criteria=dict(paw=paw)))[0]
