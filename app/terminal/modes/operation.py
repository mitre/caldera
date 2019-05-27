import asyncio
import csv
from multiprocessing import Process

from app.terminal.mode import Mode


class Operation(Mode):

    def __init__(self, services, logger):
        super().__init__(services, logger)
        self.options = [
            dict(name='name', required=1, value=None, doc='1-word name for operation'),
            dict(name='group', required=1, value=1, doc='group ID'),
            dict(name='adversary', required=1, value=1, doc='adversary ID'),
            dict(name='jitter', required=0, value='2/5', doc='seconds each agent will check in'),
            dict(name='cleanup', required=0, value=1, doc='run cleanup for each ability'),
            dict(name='stealth', required=0, value=0, doc='obfuscate the ability commands'),
            dict(name='seed', required=0, value=None, doc='absolute path to a facts csv')
        ]

    async def execute(self, cmd):
        await self.execute_mode(cmd)

    async def info(self):
        print('OPERATION allows you to build and run operations')
        print('-> search: list all started operations')
        print('-> pick [id]: show all commands for a specified operation ID')
        print('-> show options: show all configurable options an operation uses')
        print('-> show missing: show all options required to run an operation but not set')
        print('-> set [name] [value]: change an option value by name')
        print('-> unset: change all option values to None')
        print('-> run: start a new operation using the options set')
        print('-> dump [id]: view raw shell output from a specific link ID')

    async def search(self):
        operations = await self.data_svc.explode_operation()
        for op in operations:
            op.pop('host_group')
            op.pop('adversary')
            op.pop('chain')
        self.log.console_table(operations)

    async def pick(self, i):
        for op in await self.data_svc.explode_operation(criteria=dict(id=i)):
            links = []
            for link in op['chain']:
                links.append(dict(link_id=link['id'], score=link['score'], status=link['status'],
                                  collect=link['collect'], command=self.utility_svc.decode_bytes(link['command'])))
            self.log.console_table(links)

    async def run(self):
        operation = {o['name']: o['value'] for o in self.options}
        seed_file = operation.pop('seed')
        op_id = await self.data_svc.create_operation(**operation)
        if seed_file:
            with open(seed_file, 'r') as f:
                next(f)
                reader = csv.reader(f, delimiter=',')
                for line in reader:
                    fact = dict(op_id=op_id, fact=line[0], value=line[1], score=line[2], link_id=0, action=line[3])
                    await self.data_svc.dao.create('dark_fact', fact)
                    self.log.console('Pre-seeding %s' % line[0], 'blue')
        Process(target=lambda: asyncio.run(self.operation_svc.run(op_id))).start()

    async def dump(self, i):
        result = await self.data_svc.explode_results(criteria=dict(link_id=i))
        self.log.console(self.utility_svc.decode_bytes(result[0]['output']), 'yellow')
