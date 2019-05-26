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
        while True:
            try:
                cmd = await ainput(self.shell_prompt)
                mode = re.search(r'\((.*?)\)', self.shell_prompt)
                if cmd == 'help':
                    await self._print_help()
                elif cmd in self.modes.keys():
                    self.shell_prompt = 'caldera (%s)> ' % cmd
                elif mode:
                    await self.modes[mode.group(1)].execute(cmd)
                elif cmd == '':
                    pass
            except Exception:
                self.log.console('Bad command', 'red')

    async def accept_sessions(self, reader, writer):
        address = writer.get_extra_info('peername')
        connection = writer.get_extra_info('socket')
        connection.setblocking(1)
        self.modes['session'].sessions.append(connection)
        self.modes['session'].addresses.append('%s:%s' % (address[0], address[1]))
        self.log.console('New session: %s:%s' % (address[0], address[1]))

    async def _print_help(self):
        print('MODES:')
        for cmd, v in self.modes.items():
            print('--- %s' % cmd)
        print('Each mode allows the following commands:')
        print('-- info: documentation about the mode')
        print('-- search: see all entries for the mode')
        print('-- use: select an entry by ID')
        print('Operation mode allows additional commands:')
        print('-- run: execute the mode')
        print('-- options: see all args required for the "run" command')
        print('-- set: use the syntax "set arg 1" to set arg values')
        print('-- missing: shows the missing options for the "run" command to work')
        print('-- unset: reset all options')
