import json
import os
import re
from collections import defaultdict

from app.service.base_service import BaseService


class ReportingService(BaseService):

    def __init__(self):
        self.log = self.add_service('reporting_svc', self)
        self.data_svc = self.get_service('data_svc')

    async def generate_operation_report(self, op_id, agent_output=False):
        """
        Create a new operation report and write it to the logs directory
        :param op_id: operation id
        :param agent_output: bool to include agent_output with report
        :return: a JSON report
        """
        op = (await self.data_svc.explode('operation', dict(id=op_id)))[0]
        planner = (await self.data_svc.explode('planner', criteria=dict(id=op['planner'])))[0]
        report = dict(name=op['name'], id=op['id'], host_group=op['host_group'], start=op['start'], facts=op['facts'],
                      finish=op['finish'], planner=planner, adversary=op['adversary'], jitter=op['jitter'], steps=[])
        agents_steps = {a['paw']: {'agent_id': a['id'], 'steps': []} for a in op['host_group']}
        for step in op['chain']:
            ability = (await self.data_svc.explode('ability', criteria=dict(id=step['ability'])))[0]
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
                try:
                    result = (await self.data_svc.explode('result', criteria=dict(link_id=step['id'])))[0]
                    step_report['output'] = self.decode_bytes(result['output'])
                except IndexError as e:
                    continue
            agents_steps[step['paw']]['steps'].append(step_report)
        report['steps'] = agents_steps
        report['skipped_abilities'] = await self.get_skipped_abilities_by_agent(op_id=op['id'])
        return report

    async def get_skipped_abilities_by_agent(self, op_id):
        """
        Generates a list of abilities that an agent skipped (did not execute) during an operation
        :param op_id: operation id
        :return: a JSON formatted list of abilities all agents skipped
        """
        op_facts, op_results, op_state, op_group, op_adversary = await self._get_operation_data(op_id)
        abilities_by_agent = await self._get_all_possible_abilities_by_agent(hosts=op_group, adversary=op_adversary)
        skipped_abilities = []
        for agent in op_group:
            agent_skipped = defaultdict(dict)
            agent_executors = [a['executor'] for a in agent['executors']]
            agent_ran = set([(await self.data_svc.explode('ability', dict(id=ab)))[0]['ability_id'] for ab in op_results[agent['paw']]])
            for ab in abilities_by_agent[agent['paw']]['all_abilities']:
                skipped = await self._check_reason_skipped(agent=agent, ability=ab, op_facts=op_facts, state=op_state,
                                                           agent_executors=agent_executors, agent_ran=agent_ran)
                if skipped:
                    if agent_skipped[skipped['ability_id']]:
                        if agent_skipped[skipped['ability_id']]['reason_id'] < skipped['reason_id']:
                            agent_skipped[skipped['ability_id']] = skipped
                    else:
                        agent_skipped[skipped['ability_id']] = skipped
            skipped_abilities.append({agent['paw']: list(agent_skipped.values())})
        return skipped_abilities

    @staticmethod
    async def write_report(report):
        with open(os.path.join('logs', 'operation_report_' + report['name'] + '.json'), 'w') as f:
            f.write(json.dumps(report, indent=4, sort_keys=True))

    """ PRIVATE """

    @staticmethod
    async def _get_all_possible_abilities_by_agent(hosts, adversary):
        return {a['paw']: {'agent_id': a['id'], 'all_abilities': [ab for p in adversary['phases']
                                                                  for ab in adversary['phases'][p]]} for a in hosts}

    async def _get_operation_data(self, op_id):
        operation = (await self.get_service('data_svc').explode('operation', criteria=dict(id=op_id)))[0]
        op_facts = set([f['property'] for f in operation['facts']])
        op_results = {a['paw']: set([s['ability'] for s in operation['chain'] if s['paw'] == a['paw']])
                      for a in operation['host_group']}
        return op_facts, op_results, operation['state'], operation['host_group'], operation['adversary']

    async def _check_reason_skipped(self, agent, ability, op_facts, state, agent_executors, agent_ran):
        variables = re.findall(r'#{(.*?)}', self.decode(ability['test'], agent, agent['host_group']), flags=re.DOTALL)
        if ability['ability_id'] in agent_ran:
            return
        elif ability['platform'] != agent['platform']:
            return dict(reason='Wrong platform', reason_id=self.Reason.PLATFORM.value, ability_id=ability['ability_id'],
                        ability_name=ability['name'])
        elif ability['executor'] not in agent_executors:
            return dict(reason='Executor not available', reason_id=self.Reason.EXECUTOR.value,
                        ability_id=ability['ability_id'], ability_name=ability['name'])
        elif variables and not all(op_fact in op_facts for op_fact in variables):
            return dict(reason='Fact dependency not fulfilled', reason_id=self.Reason.FACT_DEPENDENCY.value,
                        ability_id=ability['ability_id'], ability_name=ability['name'])
        else:
            if (ability['platform'] == agent['platform'] and ability['executor'] in agent_executors
                    and ability['ability_id'] not in agent_ran):
                if state != 'finished':
                    return dict(reason='Operation not completed', reason_id=self.Reason.OP_RUNNING.value,
                                ability_id=ability['ability_id'], ability_name=ability['name'])
                else:
                    return dict(reason='Agent untrusted', reason_id=self.Reason.UNTRUSTED.value,
                                ability_id=ability['ability_id'], ability_name=ability['name'])
