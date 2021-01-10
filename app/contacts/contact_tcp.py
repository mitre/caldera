import asyncio
import json
import socket
import time

from app.utility.base_world import BaseWorld
from app.utility.base_object import BaseObject



class Contact(BaseWorld):

    def __init__(self, services):
        self.name = 'tcp'
        self.description = 'Accept beacons through a raw TCP socket'
        self.log = self.create_logger('contact_tcp')
        self.contact_svc = services.get('contact_svc')
        self.tcp_handler = TcpSessionHandler(services, self.log)

    async def start(self):
        loop = asyncio.get_event_loop()
        tcp = self.get_config('app.contact.tcp')
        loop.create_task(asyncio.start_server(self.tcp_handler.accept, *tcp.split(':'), loop=loop))
        loop.create_task(self.operation_loop())

    async def operation_loop(self):
        while True:
            await self.tcp_handler.refresh()
            for session in self.tcp_handler.sessions:
                _, instructions = await self.contact_svc.handle_heartbeat(paw=session.paw)
                for instruction in instructions:
                    try:
                        self.log.debug('TCP instruction: %s' % instruction.id)
                        status, _, response = await self.tcp_handler.send(session.id, self.decode_bytes(instruction.command))
                        beacon = dict(paw=session.paw, results=[dict(id=instruction.id, output=self.encode_string(response), status=status)])
                        await self.contact_svc.handle_heartbeat(**beacon)
                        await asyncio.sleep(instruction.sleep)
                    except Exception as e:
                        self.log.debug('[-] operation exception: %s' % e)
            await asyncio.sleep(20)


class TcpSessionHandler(BaseWorld):

    def __init__(self, services, log):
        self.services = services
        self.log = log
        self.sessions = []

    async def refresh(self):
        for index, session in enumerate(self.sessions):
            try:
                session.writer.write(str.encode(' '))
                await session.writer.drain()
            except socket.error:
                del self.sessions[index]

    async def accept(self, reader, writer):
        try:
            profile = await self._handshake(reader)
        except Exception as e:
            self.log.debug('Handshake failed: %s' % e)
            return
        profile['executors'] = [e for e in profile['executors'].split(',') if e]
        profile['contact'] = 'tcp'
        agent, _ = await self.services.get('contact_svc').handle_heartbeat(**profile)
        new_session = Session(id=self.generate_number(size=6), paw=agent.paw, reader=reader, writer=writer)
        self.sessions.append(new_session)
        await self.send(new_session.id, agent.paw)

    async def send(self, session_id, cmd):
        try:
            (reader, writer) = next((i.reader, i.writer) for i in self.sessions if i.id == int(session_id))
            writer.write(str.encode(' '))
            writer.write(str.encode('%s\n' % cmd))
            self.log.info(cmd)
            await writer.drain()
            try:
                response = await asyncio.wait_for(await self._attempt_connection(reader), timeout=10) # let's say 10 seconds are enough
                response = json.loads(response)
            except asyncio.TimeoutError:
                response = dict(status=1, pwd='~$ ', response=str(err))
            self.log.info(response)
            return response['status'], response["pwd"], response['response']
        except Exception as e:
            return 1, '~$ ', e

    """ PRIVATE """

    @staticmethod
    async def _handshake(reader):
        profile_bites = (await reader.readline()).strip()
        return json.loads(profile_bites)

    @staticmethod
    async def _attempt_connection(reader):
        buffer = 4096
        data = b''
        while True:
            try:
                part = await reader.read(buffer)
                data += part
                if len(part) < buffer:
                    break
            except err:
                return json.dumps(dict(status=1, pwd='~$ ', response=str(err)))
        return str(data, 'utf-8')


class Session(BaseObject):
    @property
    def unique(self):
        return self.hash('%s' % self.paw)

    def __init__(self, id, paw, reader, writer):
        super().__init__()
        self.id = id
        self.paw = paw
        self.reader = reader
        self.writer = writer

    def store(self, ram):
        existing = self.retrieve(ram['sessions'], self.unique)
        if not existing:
            ram['sessions'].append(self)
            return self.retrieve(ram['sessions'], self.unique)
        return existing








