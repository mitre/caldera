import asyncio
import traceback
from datetime import datetime
from importlib import import_module

from app.utility.logger import Logger
from app.utility.op_control import OpControl


class OperationService(OpControl):

    def __init__(self, data_svc, utility_svc, planner):
        super().__init__(data_svc.dao)
        self.data_svc = data_svc
        self.utility_svc = utility_svc
        self.loop = asyncio.get_event_loop()
        self.log = Logger('operation')
        planning_module = import_module(planner)
        self.planner = getattr(planning_module, 'LogicalPlanner')(self.data_svc, self.utility_svc, self.log)

    async def resume(self):
        for op in await self.data_svc.dao.get('core_operation'):
            if not op['finish']:
                self.loop.create_task(self.run(op['id']))

    async def close_operation(self, op_id):
        self.log.debug('Operation complete: %s' % op_id)
        update = dict(finish=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        await self.data_svc.dao.update('core_operation', key='id', value=op_id, data=update)

    async def run(self, op_id):
        self.log.debug('Starting operation: %s' % op_id)
        operation = await self.data_svc.explode_operation(dict(id=op_id))
        try:
            for phase in operation[0]['adversary']['phases']:
                self.log.debug('Operation phase %s: started' % phase)
                await self.planner.execute(operation[0], phase)
                self.log.debug('Operation phase %s: completed' % phase)
                await self.data_svc.dao.update('core_operation', key='id', value=op_id, data=dict(phase=phase))
                operation = await self.data_svc.explode_operation(dict(id=op_id))
            if operation[0]['cleanup']:
                await self.cleanup(op_id)
            await self.close_operation(op_id)
        except Exception:
            traceback.print_exc()

    async def cleanup(self, op_id):
        self.log.debug('Running cleanup on: %s' % op_id)
        clean_commands = await self.data_svc.dao.get('core_cleanup', dict(op_id=op_id))
        for c in reversed(clean_commands):
            link = dict(op_id=c['op_id'], host_id=c['agent_id'], ability_id=c['ability_id'], decide=datetime.now(),
                        command=c['command'], score=0, jitter=1)
            await self.data_svc.create_link(link)
        await self.cleanup_operation(op_id)