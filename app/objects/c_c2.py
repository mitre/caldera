import asyncio
import json

from datetime import datetime

from app.objects.c_agent import Agent
from app.utility.base_object import BaseObject


class C2(BaseObject):

    @property
    def unique(self):
        return '%s%s' % (self.module, self.config)

    def __init__(self, services, module, config, name):
        self.name = name
        self.module = module
        self.config = config
        self.data_svc = services.get('data_svc')
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

    def valid_config(self):
        """
        Function that allows data_svc to check that c2 channels have valid configuration info.
        Needs to be overwritten by subclasses
        :return: True if config is valid, False if not
        """
        return False

    def start(self, app):
        """
        Default c2 task creation, useful for Active-style c2. Passive style c2 channels should override this function
        :param app:
        :return:
        """
        loop = asyncio.get_event_loop()
        loop.create_task(self._c2_loop())

    """ PRIVATE """

    async def _c2_loop(self):
        while True:
            beacons, results = [], []
            try:
                beacons = await self.get_beacons()
            except Exception:
                self.log.debug('Receiving beacons over c2 (%s) failed!' % self.name)
            try:
                results = await self.get_results()
            except Exception:
                self.log.debug('Retrieving results over c2 (%s) failed!' % self.name)
            for data in results:
                data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                await self.save_results(data['id'], data['output'], data['status'], data['pid'])
            for beacon in beacons:
                beacon['c2'] = self.name
                agent = await self.handle_heartbeat(**beacon)
                instructions = await self.get_instructions(beacon['paw'])
                payloads = self._get_payloads(instructions)
                payload_contents = await self._get_payload_content(payloads, beacon)
                try:
                    await self.post_payloads(payload_contents, beacon['paw'])
                except Exception:
                    self.log.warning('Posting payload over c2 (%s) failed!' % self.name)
                response = dict(sleep=await agent.calculate_sleep(), instructions=instructions)
                text = self.self.encode_string(json.dumps(response))
                try:
                    await self.post_instructions(text, beacon['paw'])
                except Exception:
                    self.log.warning('Posting instructions over c2 (%s) failed!' % self.name)
            await asyncio.sleep(10)

    """ PRIVATE """

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
