import json
from datetime import datetime

from app.service.base_service import BaseService


class AgentService(BaseService):

    def __init__(self):
        self.log = self.add_service('agent_svc', self)

    async def handle_heartbeat(self, paw, platform, server, group, executor):
        self.log.debug('HEARTBEAT (%s)' % paw)
        agent = await self.get_service('data_svc').explode_agents(criteria=dict(paw=paw))
        now = self.get_current_timestamp()
        if agent:
            await self.get_service('data_svc').update('core_agent', 'paw', paw, data=dict(last_seen=now, executor=executor))
            return agent[0]
        else:
            queued = dict(last_seen=now, paw=paw, platform=platform, server=server, host_group=group, executor=executor)
            await self.get_service('data_svc').create_agent(agent=queued)
            return (await self.get_service('data_svc').explode_agents(criteria=dict(paw=paw)))[0]

    async def get_instructions(self, paw):
        commands = await self.get_service('data_svc').explode_chain(criteria=dict(paw=paw))
        instructions = []
        for link in [c for c in commands if not c['collect']]:
            await self.get_service('data_svc').update('core_chain', key='id', value=link['id'],
                                                      data=dict(collect=datetime.now()))
            payload = await self._gather_payload(link['ability'])
            instructions.append(json.dumps(dict(id=link['id'],
                                                sleep=link['jitter'],
                                                command=link['command'],
                                                cleanup=link['cleanup'],
                                                payload=payload)))
        return json.dumps(instructions)

    async def save_results(self, link_id, output, status):
        await self.get_service('data_svc').create_result(result=dict(link_id=link_id, output=output))
        await self.get_service('data_svc').update('core_chain', key='id', value=link_id,
                                                  data=dict(status=int(status),
                                                            finish=self.get_current_timestamp()))
        return json.dumps(dict(status=True))

    """ PRIVATE """

    async def _gather_payload(self, ability_id):
        payload = await self.get_service('data_svc').explode_payloads(criteria=dict(ability=ability_id))
        return payload[0]['payload'] if payload else ''
