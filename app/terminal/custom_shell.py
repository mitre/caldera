import asyncio
import csv
import re
from multiprocessing import Process

from aioconsole import ainput

from app.terminal.listening_post import Listener
from app.utility.logger import Logger


class CustomShell(Listener):

    def __init__(self, services):
        self.log = Logger('terminal')
        super().__init__(self.log)
        self.shell_prompt = 'caldera> '
        self.data_svc = services.get('data_svc')
        self.utility_svc = services.get('utility_svc')
        self.operation_svc = services.get('operation_svc')
        self.help = dict(
            help=dict(help='Show this help'),
            sessions=dict(help='Show active sessions'),
            enter=dict(help='Enter a session by index')
        )
        self.modes = dict(
            agent=dict(view=lambda: self.view_agent(),
                       pick=lambda i: self.pick_agent(i)),
            ability=dict(view=lambda: self.view_ability(),
                         pick=lambda i: self.pick_ability(i)),
            adversary=dict(view=lambda: self.view_adversary(),
                           pick=lambda i: self.pick_adversary(i)),
            operation=dict(view=lambda: self.view_operation(),
                           pick=lambda i: self.pick_operation(i),
                           run=lambda: self.run_operation(),
                           options=[
                               dict(name='name', required=1, default=None, doc='1-word name for operation'),
                               dict(name='group', required=1, default=1, doc='group ID'),
                               dict(name='adversary', required=1, default=1, doc='adversary ID'),
                               dict(name='jitter', required=0, default='2/5', doc='seconds each agent will check in'),
                               dict(name='cleanup', required=0, default=1, doc='run cleanup for each ability'),
                               dict(name='stealth', required=0, default=0, doc='obfuscate the ability commands'),
                               dict(name='seed', required=0, default=None, doc='absolute path to a facts csv')
                           ])
        )

    async def start_shell(self):
        while True:
            try:
                cmd = await ainput(self.shell_prompt)
                mode = re.search(r'\((.*?)\)', self.shell_prompt)
                if cmd == 'help':
                    await self.print_help()
                elif cmd in self.modes.keys():
                    self.shell_prompt = 'caldera (%s)> ' % cmd
                elif mode:
                    await self.execute_mode(mode.group(1), cmd)
                elif cmd == 'sessions':
                    await self.list_sessions()
                elif cmd.startswith('enter'):
                    await self.send_target_commands(int(cmd.split(' ')[-1]))
                elif cmd == '':
                    pass
                else:
                    self.log.console('Bad command', 'red')
            except Exception:
                self.log.console('Bad command', 'red')

    async def print_help(self):
        self.log.console('COMMANDS:', 'yellow')
        for cmd, v in self.help.items():
            self.log.console('--- %s: %s' % (cmd, v['help']), 'yellow')
        self.log.console('MODES:', 'yellow')
        for cmd, v in self.modes.items():
            self.log.console('--- %s' % cmd, 'yellow')
        self.log.console('Each mode allows the following commands:', 'yellow')
        self.log.console('-- view: see all entries for the mode', 'yellow')
        self.log.console('-- pick: select an entry by ID', 'yellow')
        self.log.console('-- back: exit the mode', 'yellow')
        self.log.console('Operation mode allows additional commands:', 'yellow')
        self.log.console('-- run: execute the mode', 'yellow')
        self.log.console('-- options: see all args required for the "run" command', 'yellow')
        self.log.console('-- set: use the syntax "set arg 1" to set arg values', 'yellow')
        self.log.console('-- missing: shows the missing options for the "run" command to work', 'yellow')
        self.log.console('-- unset: reset all options', 'yellow')

    async def execute_mode(self, mode, cmd):
        try:
            chosen = self.modes.get(mode)
            if cmd == 'back':
                self.shell_prompt = 'caldera> '
            elif cmd == 'options':
                self.log.console_table(chosen['options'])
            elif cmd.startswith('set'):
                pieces = cmd.split(' ')
                option = next((o for o in chosen['options'] if o['name'] == pieces[1]), False)
                option['default'] = pieces[2]
            elif cmd == 'unset':
                for option in chosen['options']:
                    option['default'] = None
            elif cmd == 'missing':
                missing = [option for option in chosen['options'] if option['default'] is None and option['required']]
                self.log.console_table([missing])
            elif len(cmd.split(' ')) == 2:
                pieces = cmd.split(' ')
                await self.modes[mode][pieces[0]](pieces[1])
            elif cmd == '':
                pass
            else:
                await self.modes[mode][cmd]()
        except IndexError:
            self.log.console('No results found', 'red')
        except Exception:
            self.log.console('Bad command', 'red')

    async def view_agent(self):
        self.log.console_table(await self.data_svc.explode_agents())

    async def pick_agent(self, i):
        self.log.console_table(await self.data_svc.explode_agents(criteria=dict(id=i)))

    async def view_ability(self):
        abilities = []
        for i, a in enumerate(await self.data_svc.explode_abilities()):
            abilities.append(dict(id=i, technique=a['technique']['attack_id'], executor=a['executor'],
                                  name=a['name'], description=a['description']))
        self.log.console_table(abilities)

    async def pick_ability(self, i):
        abilities = await self.data_svc.explode_abilities()
        for a in await self.data_svc.explode_abilities(criteria=dict(id=abilities[int(i)]['id'])):
            self.log.console_table([dict(executor=a['executor'],
                                         test=self.utility_svc.decode_bytes(a['test']),
                                         cleanup=self.utility_svc.decode_bytes(a['cleanup']))])

    async def view_adversary(self):
        adversaries = await self.data_svc.explode_adversaries()
        for adv in adversaries:
            adv.pop('phases')
        self.log.console_table(adversaries)

    async def pick_adversary(self, i):
        data = [dict(phase=phase, executor=ab['executor'], test=self.utility_svc.decode_bytes(ab['test']))
                for a in await self.data_svc.explode_adversaries(criteria=dict(id=i))
                for phase, abilities in a['phases'].items()
                for ab in abilities]
        self.log.console_table(data)

    async def view_operation(self):
        operations = await self.data_svc.explode_operation()
        for op in operations:
            op.pop('host_group')
            op.pop('adversary')
            op.pop('chain')
        self.log.console_table(operations)

    async def pick_operation(self, i):
        for op in await self.data_svc.explode_operation(criteria=dict(id=i)):
            links = []
            for link in op['chain']:
                links.append(dict(score=link['score'], status=link['status'], collect=link['collect'],
                                  command=self.utility_svc.decode_bytes(link['command'])))
            self.log.console_table(links)

    async def run_operation(self):
        operation = {o['name']: o['default'] for o in self.modes['operation']['options']}
        seed_file = operation.pop('seed')
        op_id = await self.data_svc.create_operation(**operation)
        if seed_file:
            with open(seed_file, 'r') as f:
                next(f)
                reader = csv.reader(f, delimiter=',')
                for line in reader:
                    fact = dict(op_id=op_id, fact=line[0], value=line[1], score=line[2], link_id=0, action=line[3])
                    asyncio.run(self.data_svc.dao.create('dark_fact', fact))
                    self.log.console('Pre-seeding %s' % line[0])
        Process(target=lambda: asyncio.run(self.operation_svc.run(op_id))).start()
