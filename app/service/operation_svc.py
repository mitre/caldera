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
        for op in await self.data_svc.explode_operation():
            if not op['finish']:
                self.loop.create_task(self.run(op['id']))

    async def close_operation(self, operation):
        await self.get_service('planning_svc').create_cleanup_links(operation)
        self.log.debug('Operation complete: %s' % operation['id'])
        update = dict(finish=self.get_current_timestamp(), state=self.op_states['FINISHED'])
        await self.data_svc.update('core_operation', key='id', value=operation['id'], data=update)
        await self._generate_operation_report(operation['id'])

    async def run(self, op_id):
        self.log.debug('Starting operation: %s' % op_id)
        operation = await self.data_svc.explode_operation(dict(id=op_id))
        try:
            planner = await self._get_planning_module(operation[0]['planner'])
            for phase in operation[0]['adversary']['phases']:
                operation_phase_name = 'Operation %s (%s) phase %s' % (op_id, operation[0]['name'], phase)
                self.log.debug('%s: started' % operation_phase_name)
                operation = await self.data_svc.explode_operation(dict(id=op_id))
                await planner.execute(operation[0], phase)
                self.log.debug('%s: completed' % operation_phase_name)
                await self.data_svc.update('core_operation', key='id', value=op_id,
                                                          data=dict(phase=phase))
                await self.get_service('parsing_svc').parse_facts(operation[0])
            await self.close_operation(operation[0])
        except Exception:
            traceback.print_exc()

    """ PRIVATE """

    async def _generate_operation_report(self, op_id):
        op = (await self.data_svc.explode_operation(dict(id=op_id)))[0]
        planner = await self.data_svc.explode_planners(criteria=dict(id=op['planner']))
        adversary = await self.data_svc.explode_adversaries(criteria=dict(id=op['adversary_id']))

        report = dict(name=op['name'], id=op['id'], host_group=op['host_group'], start=op['start'],
                      finish=op['finish'], planner=planner[0]['name'], adversary=adversary[0]['name'],
                      steps=[])

        for step in op['chain']:
            ability = (await self.data_svc.explode_abilities(criteria=dict(id=step['ability'])))[0]
            technique_tactic = ability['technique']['tactic']
            technique_name = ability['technique']['name']
            technique_id = ability['technique']['attack_id']
            command = self.decode_bytes(step['command'])
            s = dict(id=ability['ability_id'], paw=step['paw'],
                     command=command, delegated=step['collect'],
                     run=step['finish'], status=step['status'],
                     description=ability['description'], name=ability['name'], tactic=technique_tactic,
                     technique_name=technique_name, technique_id=technique_id)
            report['steps'].append(s)
        operation_data = json.dumps(report, sort_keys=True, indent=4, separators=(',', ': '))
        with open(os.path.join('logs', 'operation_report_' + op['name'] + '.json'), 'w') as f:
            f.write(operation_data)

    async def _get_planning_module(self, planner_id):
        chosen_planner = await self.data_svc.explode_planners(dict(id=planner_id))
        planning_module = import_module(chosen_planner[0]['module'])
        return getattr(planning_module, 'LogicalPlanner')(self.get_service('planning_svc'),
                                                          **chosen_planner[0]['params'])
