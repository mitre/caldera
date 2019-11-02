import asyncio
import json
from datetime import datetime

from app.objects.c_agent import Agent
from app.service.base_service import BaseService


class AgentService(BaseService):

    def __init__(self, untrusted_timer):
        self.log = self.add_service('agent_svc', self)
        self.data_svc = self.get_service('data_svc')
        self.loop = asyncio.get_event_loop()
        self.untrusted_timer = untrusted_timer

    async def start_sniffer_untrusted_agents(self):
        """
        Cyclic function that repeatedly checks if there are agents to be marked as untrusted
        :return: None
        """
        next_check = self.untrusted_timer
        try:
            while True:
                await asyncio.sleep(next_check + 1)
                trusted_agents = await self.data_svc.locate('agents', match=dict(trusted=1))
                next_check = self.untrusted_timer
                for a in trusted_agents:
                    last_trusted_seen = datetime.strptime(a.last_trusted_seen, '%Y-%m-%d %H:%M:%S')
                    silence_time = (datetime.now() - last_trusted_seen).total_seconds()
                    if silence_time > (self.untrusted_timer + a.sleep_max):
                        await self.data_svc.store(Agent(paw=a.paw, trusted=0))
                    else:
                        trust_time_left = self.untrusted_timer - silence_time
                        if trust_time_left < next_check:
                            next_check = trust_time_left
        except Exception as e:
            self.log.error('[!] start_sniffer_untrusted_agents: %s' % e)

    async def handle_heartbeat(self, paw, platform, server, group, executors, architecture, location, pid, ppid, sleep, privilege):
        """
        Accept all components of an agent profile and save a new agent or register an updated heartbeat.
        :param paw:
        :param platform:
        :param server:
        :param group:
        :param executors:
        :param architecture:
        :param location:
        :param pid:
        :param ppid:
        :return: the agent object from explode
        """
        self.log.debug('HEARTBEAT (%s)' % paw)
        now = self.get_current_timestamp()
        agent = Agent(last_seen=now, paw=paw, platform=platform, server=server, group=group, location=location,
                      architecture=architecture, pid=pid, ppid=ppid, trusted=True, last_trusted_seen=now,
                      executors=executors, privilege=privilege)
        if await self.data_svc.locate('agents', dict(paw=paw)):
            return await self.data_svc.store(agent)
        agent.sleep_min = agent.sleep_max = sleep
        return await self.data_svc.store(agent)

    async def get_instructions(self, paw):
        """
        Get next set of instructions to execute
        :param paw:
        :return: a list of links in JSON format
        """
        ops = await self.data_svc.locate('operations')
        instructions = []
        for link in [c for op in ops for c in op.chain if c.paw == paw and not c.collect and c.status == self.LinkState.EXECUTE.value]:
            link.collect = datetime.now()
            payload = link.ability.payload if link.ability.payload else ''
            instructions.append(json.dumps(dict(id=link.id,
                                                sleep=link.jitter,
                                                command=link.command,
                                                executor=link.ability.executor,
                                                payload=payload)))
        return json.dumps(instructions)

    async def save_results(self, link_id, output, status, pid):
        """
        Save the results from a single executed link
        :param link_id:
        :param output:
        :param status:
        :param pid:
        :return: a JSON status message
        """
        try:
            for op in await self.data_svc.locate('operations', match=dict(finish=None)):
                link = next((l for l in op.chain if l.id == int(float(link_id))), None)
                link.pid = int(pid)
                link.finish = self.get_current_timestamp()
                link.status = int(status)
                if output:
                    with open('data/results/%s' % int(float(link_id)), 'w') as out:
                        out.write(output)
                    asyncio.create_task(link.parse(op))
                await self.data_svc.store(Agent(paw=link.paw))
                return json.dumps(dict(status=True))
        except Exception as e:
            self.log.error('[!] save_results: %s' % e)
