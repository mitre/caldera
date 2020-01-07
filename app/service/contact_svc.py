import asyncio
import json
from datetime import datetime

from app.objects.c_agent import Agent
from app.utility.base_service import BaseService


class ContactService(BaseService):

    def __init__(self):
        self.log = self.add_service('contact_svc', self)
        self.contacts = []

    async def register(self, contact):
        try:
            if contact.valid_config() and contact.enabled:
                await self._start_c2_channel(contact=contact)
                self.log.debug('Started %s command and control channel' % contact.name)
            else:
                self.log.debug('%s command and control channel not started' % contact.name)
        except Exception as e:
            self.log.error('Failed to start %s command and control channel: %s' % (contact.name, e))

    async def handle_heartbeat(self, paw, platform, server, group, host, username, executors, architecture, location,
                               pid, ppid, sleep, privilege, c2, exe_name):
        """
        Accept all components of an agent profile and save a new agent or register an updated heartbeat.

        :param paw:
        :param platform:
        :param server:
        :param group:
        :param host:
        :param username:
        :param executors:
        :param architecture:
        :param location:
        :param pid:
        :param ppid:
        :param sleep:
        :param privilege:
        :return: the agent object from explode
        """
        agent = Agent(paw=paw, host=host, username=username, platform=platform, server=server, location=location,
                      executors=executors, architecture=architecture, pid=pid, ppid=ppid, privilege=privilege, c2=c2,
                      exe_name=exe_name)
        if await self.get_service('data_svc').locate('agents', dict(paw=paw)):
            return await self.get_service('data_svc').store(agent)
        agent.sleep_min = agent.sleep_max = sleep
        agent.group = group
        agent.trusted = True
        return await self.get_service('data_svc').store(agent)

    async def get_instructions(self, paw):
        """
        Get next set of instructions to execute

        :param paw:
        :return: a list of links in JSON format
        """
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

    async def save_results(self, id, output, status, pid):
        """
        Save the results from a single executed link

        :param id:
        :param output:
        :param status:
        :param pid:
        :return: a JSON status message
        """
        try:
            loop = asyncio.get_event_loop()
            for op in await self.get_service('data_svc').locate('operations', match=dict(finish=None)):
                link = next((l for l in op.chain if l.unique == id), None)
                if link:
                    link.pid = int(pid)
                    link.finish = self.get_service('data_svc').get_current_timestamp()
                    link.status = int(status)
                    if output:
                        with open('data/results/%s' % id, 'w') as out:
                            out.write(output)
                        loop.create_task(link.parse(op))
                    await self.get_service('data_svc').store(Agent(paw=link.paw))
                    return json.dumps(dict(status=True))
        except Exception:
            pass

    """ PRIVATE """

    async def _start_c2_channel(self, contact):
        loop = asyncio.get_event_loop()
        loop.create_task(contact.start())
        self.contacts.append(contact)
