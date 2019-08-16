import json
from datetime import datetime


class AgentService:

    def __init__(self, data_svc, utility_svc):
        self.data_svc = data_svc
        self.utility_svc = utility_svc
        self.log = self.utility_svc.create_logger('agent_svc')

    async def handle_heartbeat(self, paw, platform, server, group):
        self.log.debug('HEARTBEAT (%s)' % paw)
        agent = await self.data_svc.explode_agents(criteria=dict(paw=paw))
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if agent:
            await self.data_svc.update('core_agent', 'paw', paw, data=dict(last_seen=now))
            return agent[0]
        else:
            queued = dict(last_seen=now, paw=paw, platform=platform, server=server, host_group=group)
            await self.data_svc.create_agent(agent=queued)
            return (await self.data_svc.explode_agents(criteria=dict(paw=paw)))[0]

    async def get_instructions(self, paw):
        commands = await self.data_svc.explode_chain(criteria=dict(paw=paw))
        instructions = []
        for link in [c for c in commands if not c['collect']]:
            await self.data_svc.update('core_chain', key='id', value=link['id'], data=dict(collect=datetime.now()))
            payload = await self._gather_payload(link['ability'])
            instructions.append(json.dumps(dict(id=link['id'],
                                                sleep=link['jitter'],
                                                command=link['command'],
                                                cleanup=link['cleanup'],
                                                payload=payload)))
        return json.dumps(instructions)

    async def save_results(self, link_id, output, status):
        finished = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await self.data_svc.create_result(result=dict(link_id=link_id, output=output))
        await self.data_svc.update('core_chain', key='id', value=link_id,
                                   data=dict(status=int(status), finish=finished))
        return json.dumps(dict(status=True))

    """ PRIVATE """

    async def _gather_payload(self, ability_id):
        payload = await self.data_svc.explode_payloads(criteria=dict(ability=ability_id))
        return payload[0]['payload'] if payload else ''
