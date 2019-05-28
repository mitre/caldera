import asyncio
import glob
import re

from aioconsole import ainput

from app.terminal.modes.ability import Ability
from app.terminal.modes.adversary import Adversary
from app.terminal.modes.agent import Agent
from app.terminal.modes.operation import Operation
from app.terminal.modes.session import Session
from app.utility.logger import Logger


class CustomShell:

    def __init__(self, services):
        self.log = Logger('terminal')
        self.shell_prompt = 'caldera> '
        self.modes = dict(
            session=Session(services, self.log),
            agent=Agent(services, self.log),
            ability=Ability(services, self.log),
            adversary=Adversary(services, self.log),
            operation=Operation(services, self.log)
        )

    async def start_shell(self):
        await asyncio.sleep(1)
        while True:
            try:
                cmd = await ainput(self.shell_prompt)
                self.log.debug(cmd)
                mode = re.search(r'\((.*?)\)', self.shell_prompt)
                if cmd == 'help':
                    await self._print_help()
                elif cmd.startswith('log'):
                    await self._print_logs(int(cmd.split(' ')[1]))
                elif cmd in self.modes.keys():
                    self.shell_prompt = 'caldera (%s)> ' % cmd
                elif mode:
                    await self.modes[mode.group(1)].execute(cmd)
                elif cmd == '':
                    pass
                else:
                    self.log.console('Bad command - are you in the right mode?', 'red')
            except Exception as e:
                self.log.console('Bad command: %s' % e, 'red')

    async def accept_sessions(self, reader, writer):
        address = writer.get_extra_info('peername')
        connection = writer.get_extra_info('socket')
        connection.setblocking(1)
        self.modes['session'].sessions.append(connection)
        self.modes['session'].addresses.append('%s:%s' % (address[0], address[1]))
        self.log.console('New session: %s:%s' % (address[0], address[1]))

    async def _print_help(self):
        print('HELP MENU:')
        print('-> help: show this help menu')
        print('-> logs [n]: view the last n-lines of each log file')
        print('Enter one of the following modes. Once inside, enter "info" to see available commands.')
        for cmd, v in self.modes.items():
            print('-> %s' % cmd)

    @staticmethod
    async def _print_logs(n):
        for name in glob.iglob('.logs/*.log', recursive=False):
            with open(name, 'r') as f:
                print('***** %s ***** ' % name)
                lines = f.readlines()
                print(*lines[-n:])

