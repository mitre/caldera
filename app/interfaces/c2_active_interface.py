import abc
import asyncio
import json

from abc import ABC
from base64 import b64encode
from datetime import datetime


class C2Active(ABC):

    @abc.abstractmethod
    def __init__(self, name, services):
        self.name = name
        self.file_svc = services.get('file_svc')
        self.contact_svc = services.get('contact_svc')

    @abc.abstractmethod
    def get_config(self):
        """
        Returns C2 config information to be encoded into agent
        :return: config information
        """
        return

    @abc.abstractmethod
    def valid_config(self):
        """
        Check whether the yaml file configuration is valid
        :return: True or False
        """
        return

    @abc.abstractmethod
    async def get_results(self):
        """
        Retrieve all results posted to this C2 channel
        :return: results
        """
        return

    @abc.abstractmethod
    async def get_beacons(self):
        """
        Retrieve all beacons posted to this C2 channel
        :return: the beacons
        """
        return

    @abc.abstractmethod
    async def post_payloads(self, payloads, paw):
        """
        Given a list of payloads and an agent paw, posts the payload to the c2 channel
        :param payloads:
        :param paw:
        :return:
        """
        return

    @abc.abstractmethod
    async def post_instructions(self, text, paw):
        """
        Post an instruction for the agent to execute
        :param text: The instruction text for the agent to execute
        :param paw: The paw for the agent to execute
        :return:
        """
        return

    @abc.abstractmethod
    async def start(self):
        """
        Start the default active event loop for an additional C2 channel
        :return:
        """
        pass

    """ PRIVATE """

    async def _start_default_c2_active_channel(self):
        while True:
            await self._handle_results(await self.get_results())
            await self._handle_beacons(await self.get_beacons())
            await asyncio.sleep(10)

    async def _handle_results(self, results):
        for data in results:
            data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            await self.contact_svc.save_results(data['id'], data['output'], data['status'], data['pid'])

    async def _handle_beacons(self, beacons):
        for beacon in beacons:
            beacon['c2'] = self.name
            agent = await self.contact_svc.handle_heartbeat(**beacon)
            await self._send_instructions(agent, beacon, await self.contact_svc.get_instructions(beacon['paw']))

    async def _send_instructions(self, agent, beacon, instructions):
        payloads = self._get_payloads(instructions)
        payload_contents = await self._get_payload_content(payloads, beacon)
        await self.post_payloads(payload_contents, beacon['paw'])
        response = dict(sleep=await agent.calculate_sleep(), instructions=instructions)
        text = self._encode_string(json.dumps(response).encode('utf-8'))
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

    @staticmethod
    def _encode_string(s):
        return str(b64encode(s), 'utf-8')
