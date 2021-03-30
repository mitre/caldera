import asyncio
import json
import socket
import time

from app.utility.base_world import BaseWorld
from plugins.manx.app.c_session import Session


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
        index = 0

        while index < len(self.sessions):
            session = self.sessions[index]

            try:
                session.connection.send(str.encode(' '))
            except socket.error:
                self.log.debug('Error occurred when refreshing session %s. Removing from session pool.', session.id)
                del self.sessions[index]
            else:
                index += 1

    async def accept(self, reader, writer):
        try:
            profile = await self._handshake(reader)
        except Exception as e:
            self.log.debug('Handshake failed: %s' % e)
            return
        connection = writer.get_extra_info('socket')
        profile['executors'] = [e for e in profile['executors'].split(',') if e]
        profile['contact'] = 'tcp'
        agent, _ = await self.services.get('contact_svc').handle_heartbeat(**profile)
        new_session = Session(id=self.generate_number(size=6), paw=agent.paw, connection=connection)
        self.sessions.append(new_session)
        await self.send(new_session.id, agent.paw)

    async def send(self, session_id, cmd):
        try:
            conn = next(i.connection for i in self.sessions if i.id == int(session_id))
            conn.send(str.encode(' '))
            conn.send(str.encode('%s\n' % cmd))
            response = await self._attempt_connection(conn, 3)
            response = json.loads(response)
            return response['status'], response["pwd"], response['response']
        except Exception as e:
            return 1, '~$ ', e

    """ PRIVATE """

    @staticmethod
    async def _handshake(reader):
        profile_bites = (await reader.readline()).strip()
        return json.loads(profile_bites)

    @staticmethod
    async def _attempt_connection(connection, max_tries):
        attempts = 0
        buffer = 4096
        data = b''
        while True:
            try:
                part = connection.recv(buffer)
                data += part
                if len(part) < buffer:
                    break
            except BlockingIOError as err:
                if attempts > max_tries:
                    return json.dumps(dict(status=1, pwd='~$ ', response=str(err)))
                attempts += 1
                time.sleep(.1 * attempts)
        return str(data, 'utf-8')
