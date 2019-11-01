import json
import os
import re
from collections import defaultdict

from app.service.base_service import BaseService


class ReportingService(BaseService):

    def __init__(self):
        self.log = self.add_service('reporting_svc', self)
        self.data_svc = self.get_service('data_svc')

    async def generate_operation_report(self, op, agent_output=False):
        """
        Create a new operation report and write it to the logs directory
        :param op: operation id
        :param agent_output: bool to include agent_output with report
        :return: a JSON report
        """
        report = dict(name=op.name, host_group=op.agents[0].group, start=op.start.strftime('%Y-%m-%d %H:%M:%S'), steps=[],
                      finish=op.finish, planner=op.planner.name, adversary=op.adversary.display, jitter=op.jitter)
        agents_steps = {a.paw: {'steps': []} for a in op.agents}
        for step in op.chain:
            ability = (await self.data_svc.locate('abilities', match=dict(unique=step.ability.unique)))[0]
            command = self.decode_bytes(step.command)
            step_report = dict(ability_id=ability.ability_id,
                               command=command,
                               delegated=step.collect,
                               run=step.finish,
                               status=step.status,
                               platform=ability.platform,
                               executor=ability.executor,
                               pid=step.pid,
                               description=ability.description,
                               name=ability.name,
                               attack=dict(tactic=ability.tactic,
                                           technique_name=ability.technique_name,
                                           technique_id=ability.technique_id)
                               )
            agents_steps[step.paw]['steps'].append(step_report)
        report['steps'] = agents_steps
        report['skipped_abilities'] = await self.get_skipped_abilities_by_agent(op)
        return report

    async def get_skipped_abilities_by_agent(self, operation):
        """
        Generates a list of abilities that an agent skipped (did not execute) during an operation
        :param operation:
        :return: a JSON formatted list of abilities all agents skipped
        """
        op_facts, op_results, op_state, op_group, op_adversary = await self._get_operation_data(operation)
        abilities_by_agent = await self._get_all_possible_abilities_by_agent(hosts=op_group, adversary=op_adversary)
        skipped_abilities = []
        for agent in op_group:
            agent_skipped = defaultdict(dict)
            agent_executors = agent.executors
            agent_ran = set([(await self.data_svc.locate('abilities', match=dict(unique=ab)))[0].ability_id for ab in
                             op_results[agent.paw]])
            for ab in abilities_by_agent[agent.paw]['all_abilities']:
                skipped = await self._check_reason_skipped(agent=agent, ability=ab, op_facts=op_facts, state=op_state,
                                                           agent_executors=agent_executors, agent_ran=agent_ran)
                if skipped:
                    if agent_skipped[skipped['ability_id']]:
                        if agent_skipped[skipped['ability_id']]['reason_id'] < skipped['reason_id']:
                            agent_skipped[skipped['ability_id']] = skipped
                    else:
                        agent_skipped[skipped['ability_id']] = skipped
            skipped_abilities.append({agent.paw: list(agent_skipped.values())})
        return skipped_abilities

    @staticmethod
    async def write_report(report):
        with open(os.path.join('logs', 'operation_report_' + report['name'] + '.json'), 'w') as f:
            f.write(json.dumps(report, indent=4, sort_keys=True))

    """ PRIVATE """

    @staticmethod
    async def _get_all_possible_abilities_by_agent(hosts, adversary):
        return {a.paw: {'all_abilities': [ab for p in adversary.phases
                                          for ab in adversary.phases[p]]} for a in hosts}

    @staticmethod
    async def _get_operation_data(operation):
        op_results = {a.paw: set([s.ability.unique for s in operation.chain if s.paw == a.paw])
                      for a in operation.agents}
        return operation.all_facts(), op_results, operation.state, operation.agents, operation.adversary

    async def _check_reason_skipped(self, agent, ability, op_facts, state, agent_executors, agent_ran):
        variables = re.findall(r'#{(.*?)}', self.decode(ability.test, agent, agent.group), flags=re.DOTALL)
        if ability.ability_id in agent_ran:
            return
        elif ability.platform != agent.platform:
            return dict(reason='Wrong platform', reason_id=self.Reason.PLATFORM.value, ability_id=ability.ability_id,
                        ability_name=ability.name)
        elif ability.executor not in agent_executors:
            return dict(reason='Executor not available', reason_id=self.Reason.EXECUTOR.value,
                        ability_id=ability.ability_id, ability_name=ability.name)
        elif variables and not all(op_fact in op_facts for op_fact in variables):
            return dict(reason='Fact dependency not fulfilled', reason_id=self.Reason.FACT_DEPENDENCY.value,
                        ability_id=ability.ability_id, ability_name=ability.name)
        else:
            if (ability.platform == agent.platform and ability.executor in agent_executors
                    and ability.ability_id not in agent_ran):
                if state != 'finished':
                    return dict(reason='Operation not completed', reason_id=self.Reason.OP_RUNNING.value,
                                ability_id=ability.ability_id, ability_name=ability.name)
                else:
                    return dict(reason='Agent untrusted', reason_id=self.Reason.UNTRUSTED.value,
                                ability_id=ability.ability_id, ability_name=ability.name)
