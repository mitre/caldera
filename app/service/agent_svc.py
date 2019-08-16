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
