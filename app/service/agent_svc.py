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
        return await self.data_svc.store(
            Agent(last_seen=now, paw=paw, platform=platform, server=server, group=group,
                  location=location, architecture=architecture, pid=pid, ppid=ppid,
                  trusted=True, last_trusted_seen=now, sleep_min=sleep, sleep_max=sleep, executors=executors, privilege=privilege)
        )

    async def calculate_sleep(self, agent):
        return self.jitter('{}/{}'.format(agent.sleep_min, agent.sleep_max))

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
            payload = await self._gather_payload(link.ability)
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

    async def perform_action(self, link):
        """
        Perform a link in the context of an operation, respecting the 'run', 'paused' and 'run_one_step' operation
        states. Calling data_svc.save('link', link) directly will schedule the link for execution,
        ignoring the state of the operation.
        :param link:
        :return: the id of the created link
        """
        operation_svc = self.get_service('operation_svc')
        operation = (await self.data_svc.locate('operations', match=dict(name=link.operation)))[0]
        while operation.state != operation_svc.op_states['RUNNING']:
            if operation.state == operation_svc.op_states['RUN_ONE_LINK']:
                operation.add_link(link)
                operation.state = operation_svc.op_states['PAUSED']
                return link.id
            else:
                await asyncio.sleep(30)
                operation = (await self.data_svc.locate('operations', match=dict(name=link.operation)))[0]
        return operation.add_link(link)

    @staticmethod
    async def capable_agent_abilities(ability_set, agent):
        """
        Trim a list of abilities down to those an agent can actually execute
        :param ability_set:
        :param agent:
        :return:
        """
        abilities = []
        preferred = agent.executors[0]
        executors = agent.executors
        for ai in set([pa.ability_id for pa in ability_set]):
            total_ability = [ab for ab in ability_set if (ab.ability_id == ai)
                             and (ab.platform == agent.platform) and (ab.executor in executors)]
            if len(total_ability) > 0:
                val = next((ta for ta in total_ability if ta.executor == preferred), total_ability[0])
                abilities.append(val)
        return abilities

    """ PRIVATE """

    async def _gather_payload(self, ability):
        a = await self.data_svc.locate('abilities', match=dict(unique=ability.unique))
        return a[0].payload if a[0].payload else ''
