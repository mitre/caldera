import asyncio
from collections import defaultdict
from datetime import datetime
from base64 import b64decode

from app.objects.c_agent import Agent
from app.objects.secondclass.c_instruction import Instruction
from app.objects.secondclass.c_result import Result
from app.service.interfaces.i_contact_svc import ContactServiceInterface
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


class ContactService(ContactServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('contact_svc', self)
        self.contacts = []
        self.report = defaultdict(list)

    async def register(self, contact):
        try:
            await self._start_c2_channel(contact=contact)
            self.log.debug('Registered contact: %s' % contact.name)
        except Exception as e:
            self.log.error('Failed to start %s contact: %s' % (contact.name, e))

    @report
    async def handle_heartbeat(self, **kwargs):
        results = kwargs.pop('results', [])
        for agent in await self.get_service('data_svc').locate('agents', dict(paw=kwargs.get('paw', None))):
            await agent.heartbeat_modification(**kwargs)
            self.log.debug('Incoming %s beacon from %s' % (agent.contact, agent.paw))
            for result in results:
                await self._save(Result(**result))
                operation = await self.get_service('app_svc').find_op_with_link(result['id'])
                access = operation.access if operation else self.Access.RED
                await self.get_service('event_svc').fire_event('link/completed', agent=agent.display, pid=result['pid'],
                                                               access=access.value)
            return agent, await self._get_instructions(agent)
        agent = await self.get_service('data_svc').store(
            Agent.load(dict(sleep_min=self.get_config(name='agents', prop='sleep_min'),
                            sleep_max=self.get_config(name='agents', prop='sleep_max'),
                            watchdog=self.get_config(name='agents', prop='watchdog'),
                            **kwargs))
        )
        await self._add_agent_to_operation(agent)
        self.log.debug('First time %s beacon from %s' % (agent.contact, agent.paw))
        await agent.bootstrap(self.get_service('data_svc'))
        return agent, await self._get_instructions(agent)

    async def build_filename(self):
        return self.get_config(name='agents', prop='implant_name')

    async def get_contact(self, name):
        contact = [c for c in self.contacts if c.name == name]
        return contact[0]

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
                    result.output = await self._postprocess_link_result(result.output, link.ability)
                    self.get_service('file_svc').write_result_file(result.id, result.output)
                    operation = await self.get_service('app_svc').find_op_with_link(result.id)
                    if not operation and not link.ability.parsers:
                        agent = await self.get_service('data_svc').locate('agents', dict(paw=link.paw))
                        loop.create_task(self.get_service('learning_svc').learn(agent[0].all_facts(), link, result.output))
                    elif not operation:
                        loop.create_task(link.parse(None, result.output))
                    elif link.ability.parsers:
                        loop.create_task(link.parse(operation, result.output))
                    else:
                        loop.create_task(self.get_service('learning_svc').learn(operation.all_facts(), link, result.output))
            else:
                self.get_service('file_svc').write_result_file(result.id, result.output)
        except Exception as e:
            self.log.debug('save_results exception: %s' % e)

    async def _postprocess_link_result(self, result, ability):
        if ability.HOOKS and ability.executor in ability.HOOKS:
            return self.encode_string(await ability.HOOKS[ability.executor].postprocess(b64decode(result)))
        return result

    async def _start_c2_channel(self, contact):
        loop = asyncio.get_event_loop()
        loop.create_task(contact.start())
        self.contacts.append(contact)

    async def _get_instructions(self, agent):
        ops = await self.get_service('data_svc').locate('operations', match=dict(finish=None))
        instructions = []
        for link in [c for op in ops for c in op.chain
                     if c.paw == agent.paw and not c.collect and c.status == c.states['EXECUTE']]:
            instructions.append(self._convert_link_to_instruction(link))
        for link in [l for l in agent.links if not l.collect]:
            instructions.append(self._convert_link_to_instruction(link))
        return instructions

    @staticmethod
    def _convert_link_to_instruction(link):
        link.collect = datetime.now()
        payloads = [] if link.cleanup else link.ability.payloads
        return Instruction(id=link.unique,
                           sleep=link.jitter,
                           command=link.command,
                           executor=link.ability.executor,
                           timeout=link.ability.timeout,
                           payloads=payloads)

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
