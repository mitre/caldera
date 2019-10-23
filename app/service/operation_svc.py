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
        for op in await self.data_svc.explode('operation'):
            if not op['finish']:
                self.loop.create_task(self.run(op['id']))

    async def close_operation(self, op_id):
        """
        Perform all close actions for an operation
        :param op_id:
        :return: None
        """
        self.log.debug('Operation complete: %s' % op_id)
        update = dict(finish=self.get_current_timestamp(), state=self.op_states['FINISHED'])
        await self.data_svc.update('operation', key='id', value=op_id, data=update)
        report = await self.reporting_svc.generate_operation_report(op_id, agent_output=False)
        await self.reporting_svc.write_report(report)

    async def run(self, op_id):
        """
        Run a new operation
        :param op_id:
        :return: None
        """
        self.log.debug('Starting operation: %s' % op_id)
        operation = await self.data_svc.explode('operation', dict(id=op_id))
        try:
            planner = await self._get_planning_module(operation[0])
            for phase in operation[0]['adversary']['phases']:
                await planner.execute(phase)
                await self._wait_for_phase_completion(operation[0])
                await self.data_svc.update('operation', key='id', value=op_id, data=dict(phase=phase))
            await self._run_cleanup_actions(op_id)
            await self.close_operation(operation[0]['id'])
        except Exception:
            traceback.print_exc()

    """ PRIVATE """

    async def _get_planning_module(self, operation):
        chosen_planner = await self.data_svc.explode('planner', dict(id=operation['planner']))
        planning_module = import_module(chosen_planner[0]['module'])
        return getattr(planning_module, 'LogicalPlanner')(operation, self.get_service('planning_svc'),
                                                          **chosen_planner[0]['params'])

    async def _wait_for_phase_completion(self, operation):
        for member in operation['host_group']:
            if (not member['trusted']) and (not operation['allow_untrusted']):
                continue
            op = await self.data_svc.explode('operation', criteria=dict(id=operation['id']))
            while next((True for lnk in op[0]['chain'] if lnk['paw'] == member['paw'] and not lnk['finish'] and not lnk['status'] == self.LinkState.DISCARD.value),
                       False):
                await asyncio.sleep(3)
                if await self._trust_issues(operation, member['paw']):
                    break
                op = await self.data_svc.explode('operation', criteria=dict(id=operation['id']))

    async def _trust_issues(self, operation, paw):
        if not operation['allow_untrusted']:
            agent = await self.data_svc.explode('agent', criteria=dict(paw=paw))
            return not agent[0]['trusted']
        return False

    async def _run_cleanup_actions(self, op_id):
        operation = (await self.data_svc.explode('operation', criteria=dict(id=op_id)))[0]
        for member in operation['host_group']:
            for link in await self.get_service('planning_svc').select_cleanup_links(operation, member):
                await self.data_svc.save('link', link)
        await self._wait_for_phase_completion(operation)

