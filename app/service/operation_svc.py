import asyncio
import traceback
from importlib import import_module

from app.service.base_service import BaseService


class OperationService(BaseService):

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.log = self.add_service('operation_svc', self)
        self.op_states = dict(RUNNING='running',
                              RUN_ONE_LINK='run_one_link',
                              PAUSED='paused',
                              FINISHED='finished')
        self.data_svc = self.get_service('data_svc')
        self.reporting_svc = self.get_service('reporting_svc')

    async def resume(self):
        """
        Resume an operation that was stopped
        :return: None
        """
        for op in await self.data_svc.explode_operation():
            if not op['finish']:
                self.loop.create_task(self.run(op['id']))

    async def close_operation(self, operation):
        """
        Perform all close actions for an operation
        :param operation:
        :return: None
        """
        await self.get_service('planning_svc').create_cleanup_links(operation)
        self.log.debug('Operation complete: %s' % operation['id'])
        update = dict(finish=self.get_current_timestamp(), state=self.op_states['FINISHED'])
        await self.data_svc.update('core_operation', key='id', value=operation['id'], data=update)
        report = await self.reporting_svc.generate_operation_report(operation['id'], agent_output=True)
        await self.reporting_svc.write_report(report)

    async def run(self, op_id):
        """
        Run a new operation
        :param op_id:
        :return: None
        """
        self.log.debug('Starting operation: %s' % op_id)
        operation = await self.data_svc.explode_operation(dict(id=op_id))
        try:
            planner = await self._get_planning_module(operation[0])
            for phase in operation[0]['adversary']['phases']:
                operation_phase_name = 'Operation %s (%s) phase %s' % (op_id, operation[0]['name'], phase)
                self.log.debug('%s: started' % operation_phase_name)
                await planner.execute(phase)
                self.log.debug('%s: completed' % operation_phase_name)
                await self.data_svc.update('core_operation', key='id', value=op_id,
                                           data=dict(phase=phase))
            await self.close_operation(operation[0])
        except Exception:
            traceback.print_exc()

    """ PRIVATE """

    async def _get_planning_module(self, operation):
        chosen_planner = await self.data_svc.explode_planners(dict(id=operation['planner']))
        planning_module = import_module(chosen_planner[0]['module'])
        return getattr(planning_module, 'LogicalPlanner')(operation, self.get_service('planning_svc'),
                                                          **chosen_planner[0]['params'])