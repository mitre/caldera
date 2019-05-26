import asyncio
import csv
from multiprocessing import Process

from app.terminal.mode import Mode


class Operation(Mode):

    def __init__(self, services, logger):
        super().__init__(services, logger)

    async def info(self):
        print('OPERATION mode allows you to build and run operations')

    async def search(self):
        operations = await self.data_svc.explode_operation()
        for op in operations:
            op.pop('host_group')
            op.pop('adversary')
            op.pop('chain')
        self.log.console_table(operations)

    async def use(self, i):
        for op in await self.data_svc.explode_operation(criteria=dict(id=i)):
            links = []
            for link in op['chain']:
                links.append(dict(score=link['score'], status=link['status'], collect=link['collect'],
                                  command=self.utility_svc.decode_bytes(link['command'])))
            self.log.console_table(links)

    async def execute(self, cmd):
        await self.execute_mode(cmd)

    async def run(self):
        operation = {o['name']: o['value'] for o in self.modes['operation']['options']}
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

