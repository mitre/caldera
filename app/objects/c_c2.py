import asyncio
import json
import abc

from datetime import datetime

from app.objects.c_agent import Agent
from app.utility.base_object import BaseObject


class C2(BaseObject, abc.ABC):

    @property
    def unique(self):
        return '%s%s' % (self.module, self.config)

    def __init__(self, services, module, config, name):
        self.name = name
        self.module = module
        self.config = config
        self.data_svc = services.get('data_svc')
        self.file_svc = services.get('file_svc')
        self.log = services.get('app_svc').create_logger('c2')

    async def handle_heartbeat(self, paw, platform, server, group, host, username, executors, architecture, location,
                               pid, ppid, sleep, privilege, c2):
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
        self.log.debug('HEARTBEAT (%s) (%s)' % (c2, paw))
        agent = Agent(paw=paw, host=host, username=username, platform=platform, server=server, location=location,
                      executors=executors, architecture=architecture, pid=pid, ppid=ppid, privilege=privilege, c2=c2)
        if await self.data_svc.locate('agents', dict(paw=paw)):
            return await self.data_svc.store(agent)
        agent.sleep_min = agent.sleep_max = sleep
        agent.group = group
        agent.trusted = True
        return await self.data_svc.store(agent)

    async def get_instructions(self, paw):
        """
        Get next set of instructions to execute
        :param paw:
        :return: a list of links in JSON format
        """
        ops = await self.data_svc.locate('operations', match=dict(finish=None))
        instructions = []
        for link in [c for op in ops for c in op.chain
                     if c.paw == paw and not c.collect and c.status == c.states['EXECUTE']]:
            link.collect = datetime.now()
            payload = link.ability.payload if link.ability.payload else ''
            instructions.append(json.dumps(dict(id=link.unique,
                                                sleep=link.jitter,
                                                command=link.command,
                                                executor=link.ability.executor,
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
            for op in await self.data_svc.locate('operations', match=dict(finish=None)):
                link = next((l for l in op.chain if l.unique == id), None)
                if link:
                    link.pid = int(pid)
                    link.finish = self.data_svc.get_current_timestamp()
                    link.status = int(status)
                    if output:
                        with open('data/results/%s' % id, 'w') as out:
                            out.write(output)
                        loop.create_task(link.parse(op))
                    await self.data_svc.store(Agent(paw=link.paw))
                    return json.dumps(dict(status=True))
        except Exception as e:
            self.log.error('[!] save_results: %s' % e)

    def store(self, ram):
        """
        Store the object in ram
        :param ram:
        :return:
        """
        existing = self.retrieve(ram['c2'], self.unique)
        if not existing:
            ram['c2'].append(self)
            return self.retrieve(ram['c2'], self.unique)
        return existing

    @abc.abstractmethod
    def valid_config(self):
        """
        Function that allows data_svc to check that c2 channels have valid configuration info.
        Needs to be overwritten by subclasses
        :return: True if config is valid, False if not
        """
        return

    @abc.abstractmethod
    def start(self, app):
        """
        Override this function to launch a C2 channel. Use the default c2_loop for Active-style c2 or override the
        function. Passive style c2 channels should override this function
        :param app:
        :return:
        """
        return

    """ PRIVATE """

    async def _default_active_c2_loop(self):
        while True:
            await self._handle_results(await self.get_results())
            await self._handle_beacons(await self.get_beacons())
            await asyncio.sleep(10)

    async def _handle_results(self, results):
        for data in results:
            data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            await self.save_results(data['id'], data['output'], data['status'], data['pid'])

    async def _handle_beacons(self, beacons):
        for beacon in beacons:
            beacon['c2'] = self.name
            agent = await self.handle_heartbeat(**beacon)
            await self._send_instructions(agent, beacon, await self.get_instructions(beacon['paw']))

    async def _send_instructions(self, agent, beacon, instructions):
        payloads = self._get_payloads(instructions)
        payload_contents = await self._get_payload_content(payloads, beacon)
        await self.post_payloads(payload_contents, beacon['paw'])
        response = dict(sleep=await agent.calculate_sleep(), instructions=instructions)
        text = self.encode_string(json.dumps(response))
        await self.post_instructions(text, beacon['paw'])

    @staticmethod
    def _get_payloads(instructions):
        list_instructions = json.loads(instructions)
        return [json.loads(instruction).get('payload') for instruction in list_instructions
                if json.loads(instruction).get('payload')]

    async def _get_payload_content(self, payloads, beacon):
        payload_content = []
        for p in payloads:
            if p in self.file_svc.special_payloads:
                f = await self.file_svc.special_payloads[p](dict(file=p, platform=beacon['platform']))
                payload_content.append(await self.file_svc.read_file(f))
            else:
                payload_content.append(await self.file_svc.read_file(p))
        return payload_content
