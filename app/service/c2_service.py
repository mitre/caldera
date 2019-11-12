from app.utility.base_service import BaseService
import asyncio
import json
from _datetime import datetime


class C2Service(BaseService):

    def __init__(self, services):
        self.agent_svc = services.get('agent_svc')
        self.data_svc = services.get('data_svc')
        self.file_svc = services.get('file_svc')
        self.log = self.add_service('c2_svc', self)

    async def start(self):
        """
        Starts a loop that will launch all active and enabled c2 channels
        :return:
        """
        await asyncio.sleep(2)
        while True:
            c2_channels = await self.data_svc.locate('c2', dict(enabled=True, c2_type='active'))
            for c2 in c2_channels:
                c2_module = await self.load_c2_module(c2)
                beacons = []
                results = []
                try:
                    beacons = await c2_module.get_beacons()
                except Exception:
                    self.log.debug('Receiving beacons over c2 (%s) failed!' % c2_module.name)
                try:
                    results = await c2_module.get_results()
                except Exception:
                    self.log.debug('Retrieving results over c2 (%s) failed!' % c2_module.name)
                for data in results:
                    data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    await self.agent_svc.save_results(data['id'], data['output'], data['status'], data['pid'])
                for beacon in beacons:
                    beacon['c2'] = c2_module
                    agent = await self.agent_svc.handle_heartbeat(**beacon)
                    instructions = await self.agent_svc.get_instructions(beacon['paw'])
                    payloads = self._get_payloads(instructions)
                    payload_contents = await self._get_payload_content(payloads)
                    try:
                        await c2_module.post_payloads(payload_contents, beacon['paw'])
                    except Exception:
                        self.log.warning('Posting payload over c2 (%s) failed!' % c2_module.name)
                    response = dict(sleep=await agent.calculate_sleep(), instructions=instructions)
                    text = self.agent_svc.encode_string(json.dumps(response))
                    try:
                        await c2_module.post_instructions(text, beacon['paw'])
                    except Exception:
                        self.log.warning('Posting instructions over c2 (%s) failed!' % c2_module.name)
            await asyncio.sleep(10)

    async def stop_channel(self, criteria):
        """
        Stops all c2 channels that match the provided criteria
        :param criteria:
        :return:
        """
        for c2 in await self.data_svc.locate('c2', criteria):
            c2.enabled = False

    async def start_channel(self, criteria):
        """
        Starts all c2 channels that match the provided criteria
        :param criteria:
        :return:
        """
        for c2 in await self.data_svc.locate('c2', criteria):
            c2.enabled = True

    async def load_c2_module(self, c2):
        return await self.load_module(module_type=c2.name, module_info=dict(module=c2.module, config=c2.config,
                                                                            c2_type=c2.c2_type))

    """ PRIVATE """

    @staticmethod
    def _get_payloads(instructions):
        list_instructions = json.loads(instructions)
        return [json.loads(instruction).get('payload') for instruction in list_instructions
                if json.loads(instruction).get('payload')]

    async def _get_payload_content(self, payloads):
        payload_content = []
        for p in payloads:
            if p in self.file_svc.special_payloads:
                # TODO handle special payloads
                pass
            else:
                payload_content.append(await self.file_svc.read_file(p))
        return payload_content
