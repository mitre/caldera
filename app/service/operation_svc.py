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
        self.op_states = dict(RUNNING='running',
                              RUN_ONE_LINK='run_one_link',
                              PAUSED='paused',
                              FINISHED='finished')
        self.data_svc = self.get_service('data_svc')

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
        report = await self.generate_operation_report(operation['id'], agent_output=True)
        await self._write_report(report)

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

    async def generate_operation_report(self, op_id, agent_output=False):
        """
        Create a new operation report and write it to the logs directory
        :param op_id: operation id
        :param agent_output: bool to include agent_output with report
        :return: a JSON report
        """
        op = (await self.data_svc.explode_operation(dict(id=op_id)))[0]
        planner = (await self.data_svc.explode_planners(criteria=dict(id=op['planner'])))[0]
        report = dict(name=op['name'], id=op['id'], host_group=op['host_group'], start=op['start'], facts=op['facts'],
                      finish=op['finish'], planner=planner, adversary=op['adversary'], jitter=op['jitter'], steps=[])

        for step in op['chain']:
            ability = (await self.data_svc.explode_abilities(criteria=dict(id=step['ability'])))[0]
            command = self.decode_bytes(step['command'])
            step_report = dict(ability_id=ability['ability_id'],
                               paw=step['paw'],
                               command=command,
                               delegated=step['collect'],
                               run=step['finish'],
                               status=step['status'],
                               description=ability['description'],
                               name=ability['name'],
                               attack=dict(tactic=ability['tactic'],
                                           technique_name=ability['technique_name'],
                                           technique_id=ability['technique_id'])
                               )
            if agent_output:
                result = (await self.data_svc.explode_results(criteria=dict(link_id=step['id'])))[0]
                step_report['output'] = self.decode_bytes(result['output'])
            report['steps'].append(step_report)
        return report

    """ PRIVATE """

    @staticmethod
    async def _write_report(report):
        with open(os.path.join('logs', 'operation_report_' + report['name'] + '.json'), 'w') as f:
            f.write(json.dumps(report, indent=4, sort_keys=True))

    async def _get_planning_module(self, operation):
        chosen_planner = await self.data_svc.explode_planners(dict(id=operation['planner']))
        planning_module = import_module(chosen_planner[0]['module'])
        return getattr(planning_module, 'LogicalPlanner')(operation, self.get_service('planning_svc'),
                                                          **chosen_planner[0]['params'])
