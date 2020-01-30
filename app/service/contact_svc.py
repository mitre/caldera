import asyncio
import json
import random
from datetime import datetime

from app.objects.c_agent import Agent
from app.utility.base_service import BaseService


class ContactService(BaseService):

    @property
    def sleep_min(self):
        return self._sleep_min

    @sleep_min.setter
    def sleep_min(self, v):
        if v and v != self.sleep_min:
            self._sleep_min = v

    @property
    def sleep_max(self):
        return self._sleep_max

    @sleep_max.setter
    def sleep_max(self, v):
        if v and v != self._sleep_max:
            self._sleep_max = v

    @property
    def watchdog(self):
        return self._watchdog

    @watchdog.setter
    def watchdog(self, v):
        if v and v != self.watchdog:
            self._watchdog = v

    def __init__(self, agent_config):
        self.log = self.add_service('contact_svc', self)
        self.contacts = []
        self._sleep_min = agent_config['sleep_min']
        self._sleep_max = agent_config['sleep_max']
        self._watchdog = agent_config['watchdog']
        self._file_names = agent_config['names']
        self._connection_abilities = agent_config['connection_abilities']

    async def register(self, contact):
        try:
            if contact.valid_config():
                await self._start_c2_channel(contact=contact)
                self.log.debug('Started %s command and control channel' % contact.name)
            else:
                self.log.debug('%s command and control channel not started' % contact.name)
        except Exception as e:
            self.log.error('Failed to start %s command and control channel: %s' % (contact.name, e))

    async def handle_heartbeat(self, **kwargs):
        """
        Accept all components of an agent profile and save a new agent or register an updated heartbeat.
        :param paw: the unique identifier for the calling agent
        :param kwargs: key/value pairs
        :return: the agent object, instructions to execute
        """
        for agent in await self.get_service('data_svc').locate('agents', dict(paw=kwargs.get('paw', None))):
            await agent.heartbeat_modification(**kwargs)
            self.log.debug('Incoming beacon from %s' % agent.paw)
            return agent, await self._get_instructions(agent.paw)
        father_paw = kwargs.pop('father_paw', None)
        agent = Agent(sleep_min=self.sleep_min, sleep_max=self.sleep_max, watchdog=self.watchdog, **kwargs)
        if father_paw:
            father_agents = await self.get_service('data_svc').locate('agents', dict(paw=father_paw))
            if father_agents:
                father_agent = father_agents[0]
                father_agent.add_child(agent.paw, agent.display_name)
                agent.father = (father_paw, father_agent.display_name)
                agent.child = []
            else:
                self.log.debug('Father agent not set: no agent with paw = %s' % father)
        agent = await self.get_service('data_svc').store(agent)
        self.log.debug('First time beacon from %s' % agent.paw)
        return agent, await self._get_instructions(agent.paw)

    async def save_results(self, id, output, status, pid):
        """
        Save the results from a single executed link

        :param id:
        :param output:
        :param status:
        :param pid:
        :return: a JSON status message
        """
        file_svc = self.get_service('file_svc')
        try:
            loop = asyncio.get_event_loop()
            for op in await self.get_service('data_svc').locate('operations', match=dict(finish=None)):
                link = next((l for l in op.chain if l.unique == id), None)
                if link:
                    link.pid = int(pid)
                    link.finish = self.get_service('data_svc').get_current_timestamp()
                    link.status = int(status)
                    if output:
                        link.output = output
                        file_svc.write_result_file(id, output)
                        loop.create_task(link.parse(op))
                    agent = (await self.get_service('data_svc').locate('agents', match=dict(paw=link.paw)))[0]
                    await agent.heartbeat_modification()
        except Exception:
            pass

    async def build_filename(self, platform):
        return random.choice(self._file_names.get(platform))

    """ PRIVATE """

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
            instructions.append(json.dumps(dict(id=link.unique,
                                                sleep=link.jitter,
                                                command=link.command,
                                                executor=link.ability.executor,
                                                timeout=link.ability.timeout,
                                                payload=payload)))
        return json.dumps(instructions)
