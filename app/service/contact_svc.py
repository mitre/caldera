import asyncio
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
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
                   date=BaseWorld.get_current_timestamp())
        args[0].report[agent.contact.upper()].append(log)
        return agent, instructions

    return wrapper


class ContactService(ContactServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('contact_svc', self)
        self.contacts = []
        self.tunnels = []
        self.report = defaultdict(list)

    async def register_contact(self, contact):
        try:
            await self._start_c2_channel(contact=contact)
            self.log.debug('Registered contact: %s' % contact.name)
        except Exception as e:
            self.log.error('Failed to start %s contact: %s' % (contact.name, e))

    async def deregister_contacts(self):
        try:
            for contact in self.contacts:
                await self._stop_c2_channel(contact=contact)
                self.log.debug('Deregistered contact: %s' % contact.name)
        except Exception as e:
            self.log.error('Failed to stop %s contact: %s' % (contact.name, e))

    async def register_tunnel(self, tunnel):
        try:
            await self._start_c2_tunnel(tunnel=tunnel)
            self.log.debug('Registered contact tunnel: %s', tunnel.name)
        except Exception as e:
            self.log.exception('Failed to start %s contact tunnel: %s', tunnel.name, e)

    @report
    async def handle_heartbeat(self, **kwargs):
        results = kwargs.pop('results', [])
        old_paw = kwargs.get('paw')
        if old_paw:
            kwargs['paw'] = await self._sanitize_paw(old_paw)
        for agent in await self.get_service('data_svc').locate('agents', dict(paw=kwargs.get('paw', None))):
            await agent.heartbeat_modification(**kwargs)
            self.log.debug('Incoming %s beacon from %s' % (agent.contact, agent.paw))
            for result in results:
                self.log.debug('Received result for link %s from agent %s via contact %s' % (result['id'], agent.paw,
                                                                                             agent.contact))
                await self._save(Result(**result))
                operation = await self.get_service('app_svc').find_op_with_link(result['id'])
                access = operation.access if operation else self.Access.RED
                await self.get_service('event_svc').fire_event(exchange='link', queue='completed', agent=agent.display,
                                                               pid=result['pid'], link_id=result['id'],
                                                               access=access.value)
            if results:
                return agent, []
            return agent, await self._get_instructions(agent)
        agent = await self.get_service('data_svc').store(
            Agent.load(dict(sleep_min=self.get_config(name='agents', prop='sleep_min'),
                            sleep_max=self.get_config(name='agents', prop='sleep_max'),
                            watchdog=self.get_config(name='agents', prop='watchdog'),
                            **kwargs))
        )
        await self._add_agent_to_operation(agent)
        self.log.debug('First time %s beacon from %s' % (agent.contact, agent.paw))
        data_svc = self.get_service('data_svc')
        await agent.bootstrap(data_svc)
        if agent.deadman_enabled:
            self.log.debug("Agent %s can accept deadman abilities. Will return any available deadman abilities." %
                           agent.paw)
            await agent.deadman(data_svc)
        await self.get_service('event_svc').fire_event(exchange='agent', queue='added', agent=agent.display)
        return agent, await self._get_instructions(agent)

    async def build_filename(self):
        return self.get_config(name='agents', prop='implant_name')

    async def get_contact(self, name):
        contact = [c for c in self.contacts if c.name == name]
        return contact[0]

    async def get_tunnel(self, name):
        tunnel = [t for t in self.tunnels if t.name == name]
        return tunnel[0] if len(tunnel) > 0 else None

    async def _sanitize_paw(self, input_paw):
        """
        Remove any characters from the given paw that do not fall in the following set:
            - alphanumeric characters
            - hyphen, underscore, period
        """
        return re.sub(r'[^\w.\-]', '', input_paw)

    async def _save(self, result):
        try:
            loop = asyncio.get_event_loop()
            link = await self.get_service('app_svc').find_link(result.id)
            if link:
                link.pid = int(result.pid)
                link.finish = self.get_service('data_svc').get_current_timestamp()
                link.status = int(result.status)
                if result.agent_reported_time:
                    link.agent_reported_time = self.get_timestamp_from_string(result.agent_reported_time)
                if result.output or result.stderr:
                    link.output = True
                    result.output = await self._postprocess_link_result(result.output, link)
                    command_results = json.dumps(dict(
                        stdout=self.decode_bytes(result.output, strip_newlines=False),
                        stderr=self.decode_bytes(result.stderr, strip_newlines=False),
                        exit_code=result.exit_code))
                    encoded_command_results = self.encode_string(command_results)
                    self.get_service('file_svc').write_result_file(result.id, encoded_command_results)
                    operation = await self.get_service('app_svc').find_op_with_link(result.id)
                    if not operation and not link.executor.parsers:
                        agent = await self.get_service('data_svc').locate('agents', dict(paw=link.paw))
                        loop.create_task(self.get_service('learning_svc').learn(await agent[0].all_facts(), link,
                                                                                result.output))
                    elif not operation:
                        loop.create_task(link.parse(None, result.output))
                    elif link.executor.parsers:
                        loop.create_task(link.parse(operation, result.output))
                    elif operation.use_learning_parsers:
                        all_facts = await operation.all_facts()
                        loop.create_task(self.get_service('learning_svc').learn(all_facts, link, result.output,
                                                                                operation))
            else:
                command_results = json.dumps(dict(
                    stdout=self.decode_bytes(result.output, strip_newlines=False),
                    stderr=self.decode_bytes(result.stderr, strip_newlines=False),
                    exit_code=result.exit_code))
                encoded_command_results = self.encode_string(command_results)
                self.get_service('file_svc').write_result_file(result.id, encoded_command_results)
        except Exception as e:
            self.log.exception(f'Unexpected error occurred while saving link - {e}')

    async def _postprocess_link_result(self, result, link):
        if link.ability.HOOKS and link.executor.name in link.ability.HOOKS:
            return self.encode_string(await link.ability.HOOKS[link.executor.name].postprocess(b64decode(result)))
        return result

    async def _start_c2_channel(self, contact):
        loop = asyncio.get_event_loop()
        loop.create_task(contact.start())
        self.contacts.append(contact)

    async def _start_c2_tunnel(self, tunnel):
        loop = asyncio.get_event_loop()
        loop.create_task(tunnel.start())
        self.tunnels.append(tunnel)

    async def _stop_c2_channel(self, contact):
        if hasattr(contact, 'stop'):
            await contact.stop()

    async def _get_instructions(self, agent):
        ops = await self.get_service('data_svc').locate('operations', match=dict(finish=None))
        instructions = []
        for link in [c for op in ops for c in op.chain
                     if c.paw == agent.paw and not c.collect and c.status == c.states['EXECUTE']]:
            instructions.append(self._convert_link_to_instruction(link))
        for link in [s_link for s_link in agent.links if not s_link.collect]:
            instructions.append(self._convert_link_to_instruction(link))
        return instructions

    @staticmethod
    def _convert_link_to_instruction(link):
        link.collect = datetime.now(timezone.utc)
        payloads = [] if link.cleanup else link.executor.payloads
        uploads = [] if link.cleanup else link.executor.uploads
        return Instruction(id=link.unique,
                           sleep=link.jitter,
                           command=link.command,
                           executor=link.executor.name,
                           timeout=link.executor.timeout,
                           payloads=payloads,
                           uploads=uploads,
                           deadman=link.deadman,
                           delete_payload=link.ability.delete_payload)

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
            if op.group == agent.group or not op.group:
                await op.update_operation_agents(self.get_services())
