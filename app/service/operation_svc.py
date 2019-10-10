import asyncio
import json
import os
import re
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
        agents_steps = {a['paw']: {'agent_id': a['id'], 'steps': []} for a in op['host_group']}
        for step in op['chain']:
            ability = (await self.data_svc.explode_abilities(criteria=dict(id=step['ability'])))[0]
            command = self.decode_bytes(step['command'])
            step_report = dict(ability_id=ability['ability_id'],
                               command=command,
                               delegated=step['collect'],
                               run=step['finish'],
                               status=step['status'],
                               platform=ability['platform'],
                               executor=step['executor'],
                               description=ability['description'],
                               name=ability['name'],
                               attack=dict(tactic=ability['tactic'],
                                           technique_name=ability['technique_name'],
                                           technique_id=ability['technique_id'])
                               )
            if agent_output:
                result = (await self.data_svc.explode_results(criteria=dict(link_id=step['id'])))[0]
                step_report['output'] = self.decode_bytes(result['output'])
            agents_steps[step['paw']]['steps'].append(step_report)
        report['steps'] = agents_steps
        report['skipped_abilities'] = await self.get_skipped_abilities_by_agent(op_id=op['id'])
        return report

    async def get_skipped_abilities_by_agent(self, op_id):
        """
        Generate a list of skipped abilities for agents in an operation
        :param op_id: operation id
        :return: a JSON skipped abilities list by agent
        """
        operation = (await self.get_service('data_svc').explode_operation(criteria=dict(id=op_id)))[0]
        abilities_by_agent = await self._get_all_possible_abilities_by_agent(hosts=operation['host_group'],
                                                                             adversary=operation['adversary'])
        skipped_abilities = []
        operation_facts = set([f['property'] for f in operation['facts']])
        operation_results = set([s['ability'] for s in operation['chain']])
        for agent in operation['host_group']:
            agent_skipped = []
            agent_executors = [a['executor'] for a in agent['executors']]
            for ab in abilities_by_agent[agent['paw']]['all_abilities']:
                skipped = await self._check_reason_skipped(agent=agent,
                                                           ability=ab,
                                                           op_facts=operation_facts,
                                                           op_results=operation_results,
                                                           state=operation['state'],
                                                           agent_executors=agent_executors)
                if skipped:
                    agent_skipped.append(skipped)
            skipped_abilities.append({agent['paw']: agent_skipped})
        return skipped_abilities

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

    @staticmethod
    async def _get_all_possible_abilities_by_agent(hosts, adversary):
        return {a['paw']: {'agent_id': a['id'], 'all_abilities': [ab for p in adversary['phases']
                                                                  for ab in adversary['phases'][p]]} for a in hosts}

    async def _check_reason_skipped(self, agent, ability, op_facts, op_results, state, agent_executors):
        variables = re.findall(r'#{(.*?)}',
                               await self.get_service('planning_svc').decode(ability['test'], agent,
                                                                             agent['host_group']),
                               flags=re.DOTALL)
        if ability['platform'] != agent['platform']:
            return dict(reason="Wrong platform", reason_id=self.Reason.PLATFORM.value, ability=ability)
        elif ability['executor'] not in agent_executors:
            return dict(reason="Executor not available", reason_id=self.Reason.EXECUTOR.value, ability=ability)
        elif variables and not all(op_fact in op_facts for op_fact in variables):
            return dict(reason="Fact dependency not fulfilled", reason_id=self.Reason.FACT_DEPENDENCY.value, ability=ability)
        else:
            if (ability['platform'] == agent['platform'] and ability['executor'] in agent_executors
                    and ability['id'] not in op_results):
                if state != 'finished':
                    return dict(reason="Operation not completed", reason_id=self.Reason.OP_RUNNING.value, ability=ability)
                else:
                    return dict(reason="Agent untrusted", reason_id=self.Reason.UNTRUSTED.value, ability=ability)
