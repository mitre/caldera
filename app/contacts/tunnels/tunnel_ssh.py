import os

import asyncssh

from app.utility.base_world import BaseWorld


class Tunnel(BaseWorld):
    def __init__(self, services):
        self.name = 'ssh_tunneling'
        self.description = 'Accept tunneled SSH messages'
        self.log = self.create_logger('tunnel_ssh')
        self.services = services
        self._user_name = self.get_config('app.contact.tunnel.ssh.user_name')
        self._user_password = self.get_config('app.contact.tunnel.ssh.user_password')

    async def start(self):
        ssh_endpoint = self.get_config('app.contact.tunnel.ssh.socket')
        addr, port = ssh_endpoint.split(':')
        host_key_filename = self.get_config('app.contact.tunnel.ssh.host_key_file')
        host_key_filepath = os.path.join('conf', 'ssh_keys', host_key_filename)
        host_key_passphrase = self.get_config('app.contact.tunnel.ssh.host_key_passphrase')
        try:
            host_key = asyncssh.read_private_key(host_key_filepath, passphrase=host_key_passphrase)
        except Exception:
            self.log.info('Generating temporary SSH private key. Was unable to use provided SSH private key')
            host_key = asyncssh.generate_private_key('ssh-rsa', comment='temporary key')
        try:
            await asyncssh.create_server(self.server_factory, addr, int(port),
                                         server_host_keys=[host_key])
        except Exception as e:
            self.log.error('Error starting SSH server: %s' % e)

    def server_factory(self):
        return SSHServerTunnel(self.services, self._user_name, self._user_password)


class SSHServerTunnel(asyncssh.SSHServer):
    def __init__(self, services, user_name, user_password):
        super().__init__()
        self.services = services
        self.log = BaseWorld.create_logger('ssh_server')
        self.valid_user_credentials = {
            user_name: user_password
        }

    def connection_requested(self, dest_host, dest_port, orig_host, orig_port):
        self.log.debug('Connection request from %s:%sd to %s:%s' % (orig_host, orig_port, dest_host, dest_port))
        return True

    def connection_made(self, conn):
        self.log.debug('SSH connection received from %s.' % conn.get_extra_info('peername')[0])

    def connection_lost(self, exc):
        if exc:
            self.log.error('SSH connection error: ' + str(exc))
        else:
            self.log.debug('SSH connection closed.')

    def begin_auth(self, username):
        # If the user's password is the empty string, no auth is required
        return self.valid_user_credentials.get(username) != ''

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        valid_password = self.valid_user_credentials.get(username)
        return valid_password and password == valid_password
