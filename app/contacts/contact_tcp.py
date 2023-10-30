import asyncio
import json
import socket
import time

from typing import Tuple

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
        loop.create_task(asyncio.start_server(self.tcp_handler.accept, *tcp.split(':')))
        loop.create_task(self.operation_loop())

    async def operation_loop(self):
        while True:
            await self.tcp_handler.refresh()
            for session in self.tcp_handler.sessions:
                _, instructions = await self.contact_svc.handle_heartbeat(paw=session.paw)
                for instruction in instructions:
                    try:
                        self.log.debug('TCP instruction: %s' % instruction.id)
                        status, _, response, agent_reported_time = await self.tcp_handler.send(
                            session.id,
                            self.decode_bytes(instruction.command),
                            timeout=instruction.timeout
                        )
                        beacon = dict(paw=session.paw,
                                      results=[dict(id=instruction.id, output=self.encode_string(response), status=status, agent_reported_time=agent_reported_time)])
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
        await self.send(new_session.id, agent.paw, timeout=5)

    async def send(self, session_id: int, cmd: str, timeout: int = 60) -> Tuple[int, str, str, str]:
        try:
            conn = next(i.connection for i in self.sessions if i.id == int(session_id))
            conn.send(str.encode(' '))
            time.sleep(0.01)
            conn.send(str.encode('%s\n' % cmd))
            response = await self._attempt_connection(session_id, conn, timeout=timeout)
            response = json.loads(response)
            return response['status'], response['pwd'], response['response'], response.get('agent_reported_time', '')
        except Exception as e:
            self.log.exception(e)
            return 1, '~$ ', str(e), ''

    @staticmethod
    async def _handshake(reader):
        profile_bites = (await reader.readline()).strip()
        return json.loads(profile_bites)

    async def _attempt_connection(self, session_id, connection, timeout):
        buffer = 4096
        data = b''
        waited_seconds = 0
        time.sleep(0.1)  # initial wait for fast operations.
        while True:
            try:
                part = connection.recv(buffer)
                data += part
                if len(part) < buffer:
                    break
            except BlockingIOError as err:
                if waited_seconds < timeout:
                    time.sleep(1)
                    waited_seconds += 1
                else:
                    self.log.error("Timeout reached for session %s", session_id)
                    return json.dumps(dict(status=1, pwd='~$ ', response=str(err)))
        return str(data, 'utf-8')
