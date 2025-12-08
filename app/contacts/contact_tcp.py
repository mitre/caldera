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
        self.server_task = None
        self.op_loop_task = None
        self.server = None

    async def start(self):
        loop = asyncio.get_event_loop()
        tcp = self.get_config('app.contact.tcp')
        self.server_task = loop.create_task(self.start_server(*tcp.split(':')))
        self.op_loop_task = loop.create_task(self.operation_loop())

    async def stop(self):
        if self.op_loop_task:
            self.op_loop_task.cancel()
        if self.server_task:
            self.server_task.cancel()
        _ = await asyncio.gather(self.server_task, self.op_loop_task, return_exceptions=True)

    async def start_server(self, host, port):
        try:
            self.server = await asyncio.start_server(self.tcp_handler.accept, host, port)
            async with self.server:
                await self.server.serve_forever()
        except asyncio.CancelledError:
            self.log.debug('Canceling TCP contact server task.')
            if self.server:
                self.log.debug('Closing TCP contact server.')
                self.server.close()
                await self.server.wait_closed()
                self.log.debug('Closed TCP contact server.')
            raise

    async def operation_loop(self):
        try:
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
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            self.log.debug('[-] operation exception: %s' % e)
                await asyncio.sleep(20)
        except asyncio.CancelledError:
            self.log.debug('Canceling TCP contact operation loop task.')
            for sess in self.tcp_handler.sessions:
                self.log.debug(f'Closing session {sess.id}.')
                sess.writer.close()
                await session.writer.wait_closed()
            self.log.debug('Closed TCP contact sessions.')
            raise


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
                session.writer.write(str.encode(' '))
            except socket.error:
                self.log.debug('Error occurred when refreshing session %s. Removing from session pool.', session.id)
                del self.sessions[index]
            else:
                index += 1

    async def accept(self, reader, writer):
        self.log.debug('Accepting connection.')
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
        await self.send(new_session.id, agent.paw, timeout=5)

    async def send(self, session_id: int, cmd: str, timeout: int = 60) -> Tuple[int, str, str, str]:
        try:
            session = next(i for i in self.sessions if i.id == int(session_id))
            session.writer.write(str.encode(' '))
            time.sleep(0.01)
            session.writer.write(str.encode('%s\n' % cmd))
            response = await self._attempt_connection(session_id, session.reader, timeout=timeout)
            response = json.loads(response)
            return response['status'], response['pwd'], response['response'], response.get('agent_reported_time', '')
        except Exception as e:
            self.log.exception(e)
            return 1, '~$ ', str(e), ''

    @staticmethod
    async def _handshake(reader):
        profile_bites = (await reader.readline()).strip()
        return json.loads(profile_bites)

    async def _attempt_connection(self, session_id, reader, timeout):
        buffer = 4096
        data = b''
        time.sleep(0.1)  # initial wait for fast operations.
        while True:
            try:
                part = await reader.read(buffer)
                data += part
                if len(part) < buffer:
                    break
            except Exception as err:
                self.log.error("Timeout reached for session %s", session_id)
                return json.dumps(dict(status=1, pwd='~$ ', response=str(err)))
        return str(data, 'utf-8')

