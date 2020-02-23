import asyncio
import random
from collections import defaultdict
from datetime import datetime

from app.objects.c_agent import Agent
from app.objects.secondclass.c_instruction import Instruction
from app.objects.secondclass.c_result import Result
from app.utility.base_service import BaseService
from app.utility.base_world import BaseWorld


def report(func):
    async def wrapper(*args, **kwargs):
        agent, instructions = await func(*args, **kwargs)
        log = dict(paw=agent.paw, instructions=[BaseWorld.decode_bytes(i.command) for i in instructions],
                   date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        args[0].report[agent.contact].append(log)
        return agent, instructions
    return wrapper


class ContactService(BaseService):

    @property
    def sleep_min(self):
        return self._sleep_min

    @sleep_min.setter
    def sleep_min(self, v):
        if v and v != self.sleep_min:
            self.log.debug('Agent sleep_min now = %d' % v)
            self._sleep_min = v

    @property
    def sleep_max(self):
        return self._sleep_max

    @sleep_max.setter
    def sleep_max(self, v):
        if v and v != self._sleep_max:
            self.log.debug('Agent sleep_max now = %d' % v)
            self._sleep_max = v

    @property
    def watchdog(self):
        return self._watchdog

    @watchdog.setter
    def watchdog(self, v):
        if v and v != self.watchdog:
            self.log.debug('Agent watchdog now = %d' % v)
            self._watchdog = v

    @property
    def untrusted_timer(self):
        return self._untrusted_timer

    @property
    def bootstrap_instructions(self):
        return self._bootstrap_instructions

    def __init__(self, agent_config):
        self.log = self.add_service('contact_svc', self)
        self.contacts = []
        self.report = defaultdict(list)
        self._sleep_min = agent_config['sleep_min']
        self._sleep_max = agent_config['sleep_max']
        self._watchdog = agent_config['watchdog']
        self._file_names = agent_config['names']
        self._untrusted_timer = agent_config['untrusted_timer']
        self._bootstrap_instructions = agent_config['bootstrap_abilities']

    async def register(self, contact):
        try:
            await self._start_c2_channel(contact=contact)
            self.log.debug('Registered contact: %s' % contact.name)
        except Exception as e:
            self.log.error('Failed to start %s contact: %s' % (contact.name, e))

    @report
    async def handle_heartbeat(self, **kwargs):
        """
        Accept all components of an agent profile and save a new agent or register an updated heartbeat.
        :param kwargs: key/value pairs
        :return: the agent object, instructions to execute
        """
        result = kwargs.pop('result', dict())
        for agent in await self.get_service('data_svc').locate('agents', dict(paw=kwargs.get('paw', None))):
            await agent.heartbeat_modification(**kwargs)
            self.log.debug('Incoming %s beacon from %s' % (agent.contact, agent.paw))
            if result:
                await self._save(Result(**result))
            return agent, await self._get_instructions(agent.paw)
        agent = await self.get_service('data_svc').store(Agent(
            sleep_min=self.sleep_min, sleep_max=self.sleep_max, watchdog=self.watchdog, **kwargs)
        )
        await self._add_agent_to_operation(agent)
        self.log.debug('First time %s beacon from %s' % (agent.contact, agent.paw))
        return agent, await self._get_instructions(agent.paw) + await self._get_bootstrap_instructions(agent)

    async def build_filename(self, platform):
        return random.choice(self._file_names.get(platform))

    """ PRIVATE """

    async def _save(self, result):
        try:
            loop = asyncio.get_event_loop()
            link = await self.get_service('app_svc').find_link(result.id)
            if link:
                link.pid = int(result.pid)
                link.finish = self.get_service('data_svc').get_current_timestamp()
                link.status = int(result.status)
                if result.output:
                    link.output = True
                    self.get_service('file_svc').write_result_file(result.id, result.output)
                    if link.ability.parsers:
                        operation = await self.get_service('data_svc').locate('operations', dict(id=link.operation))
                        loop.create_task(link.parse(operation[0], result.output))
                    else:
                        loop.create_task(self.get_service('learning_svc').learn(link, result.output))
        except Exception as e:
            self.log.debug('save_results exception: %s' % e)

    async def _start_c2_channel(self, contact):
        loop = asyncio.get_event_loop()
        loop.create_task(contact.start())
        self.contacts.append(contact)

    async def _get_instructions(self, paw):
        ops = await self.get_service('data_svc').locate('operations', match=dict(finish=None))
        instructions = []
        for link in [c for op in ops for c in op.chain
                     if c.paw == paw and not c.collect and c.status == c.states['EXECUTE']]:
            link.collect = datetime.now()
            payload = link.ability.payload if link.ability.payload else ''
            instructions.append(Instruction(identifier=link.unique,
                                            sleep=link.jitter,
                                            command=link.command,
                                            executor=link.ability.executor,
                                            timeout=link.ability.timeout,
                                            payload=payload))
        return instructions

    async def _get_bootstrap_instructions(self, agent):
        data_svc = self._services.get('data_svc')
        abilities = []
        for i in self._bootstrap_instructions:
            for a in await data_svc.locate('abilities', match=dict(ability_id=i)):
                abilities.append(a)
        instructions = []
        for x, i in enumerate(await agent.capabilities(abilities)):
            new_id = 'bootstrap-%s-%d' % (agent.paw, x)
            cmd = self.encode_string(agent.replace(i.test))
            instructions.append(Instruction(identifier=new_id, command=cmd, executor=i.executor))
        return instructions

    async def _add_agent_to_operation(self, agent):
        """Determine which operation(s) incoming agent belongs to and
        add it to operation.

        Note: Agent is added immediately to operation, as certain planners
        may execute single links at a time before relinquishing control back
        to c_operation.run() (when previously the operation was updated with
        new agents), and during those link executions, new agents may arise
        which the planner needs to be aware of.
        """
        for op in await self.get_service('data_svc').locate('operations', match=dict(finish=None)):
            if op.group == agent.group or op.group is None:
                await op.update_operation(self.get_services())
