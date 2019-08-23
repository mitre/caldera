import asyncio
import json
import os
import traceback
from importlib import import_module

from app.service.base_service import BaseService


class OperationService(BaseService):

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.log = self.add_service('operation_svc', self)

    async def resume(self):
        for op in await self.get_service('data_svc').explode_operation():
            if not op['finish']:
                self.loop.create_task(self.run(op['id']))

    async def close_operation(self, op_id):
        self.log.debug('Operation complete: %s' % op_id)
        update = dict(finish=self.get_current_timestamp())
        await self.get_service('data_svc').update('core_operation', key='id', value=op_id, data=update)
        await self.generate_operation_report(op_id, save=True)

    async def run(self, op_id):
        self.log.debug('Starting operation: %s' % op_id)
        operation = await self.get_service('data_svc').explode_operation(dict(id=op_id))

        try:
            planner = await self._get_planning_module(operation[0]['planner'])
            for phase in operation[0]['adversary']['phases']:
                operation_phase_name = 'Operation %s (%s) phase %s' % (op_id, operation[0]['name'], phase)
                self.log.debug('%s: started' % operation_phase_name)
                operation = await self.get_service('data_svc').explode_operation(dict(id=op_id))
                await planner.execute(operation[0], phase)
                self.log.debug('%s: completed' % operation_phase_name)
                await self.get_service('data_svc').update('core_operation', key='id', value=op_id, data=dict(phase=phase))
                await self.get_service('parsing_svc').parse_facts(operation[0])
            await self.close_operation(op_id)
        except Exception:
            traceback.print_exc()

    async def generate_operation_report(self, op_id, save=False):
        operation = (await self.get_service('data_svc').explode_operation(dict(id=op_id)))[0]
        operation['result'] = []
        for link in operation['chain']:
            results = await self.get_service('data_svc').explode_results(criteria=dict(link_id=link['id']))
            for result in results:
                result.pop('link')
                operation['result'].append(result)
        operation_data = json.dumps(operation, sort_keys=True, indent=4, separators=(',', ': '))
        if save:
            with open(os.path.join('logs', 'operation_report_' + operation['name'] + '.json'), 'w') as f:
                f.write(operation_data)
        return operation_data

    """ PRIVATE """

    async def _get_planning_module(self, planner_id):
        chosen_planner = await self.get_service('data_svc').explode_planners(dict(id=planner_id))
        planning_module = import_module(chosen_planner[0]['module'])
        return getattr(planning_module, 'LogicalPlanner')(self.get_service('planning_svc'),
                                                          **chosen_planner[0]['params'])
