import ast
import asyncio
import copy
import re
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from enum import Enum
from importlib import import_module
from random import randint

from app.objects.c_adversary import Adversary
from app.utility.base_object import BaseObject

REDACTED = '**REDACTED**'


def redact_report(report):
    redacted = copy.deepcopy(report)
    # host_group
    for agent in redacted.get('host_group', []):
        agent['group'] = REDACTED
        agent['server'] = REDACTED
        agent['location'] = REDACTED
        agent['display_name'] = REDACTED
        agent['host'] = REDACTED
    # steps
    steps = redacted.get('steps', dict())
    for agentname, agent in steps.items():
        for step in agent['steps']:
            step['description'] = REDACTED
            step['name'] = REDACTED
            step['output'] = REDACTED
    # adversary
    redacted['adversary']['name'] = REDACTED
    redacted['adversary']['description'] = REDACTED
    for phase in redacted['adversary']['phases'].values():
        for step in phase:
            step['name'] = REDACTED
            step['description'] = REDACTED
    # facts
    for fact in redacted.get('facts', []):
        fact['unique'] = REDACTED
        fact['value'] = REDACTED
    # skipped_abilities
    for s in redacted.get('skipped_abilities', []):
        for agentname, ability_list in s.items():
            for ability in ability_list:
                ability['ability_name'] = REDACTED

    return redacted


class Operation(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.id)

    @property
    def display(self):
        return self.clean(dict(id=self.id, name=self.name, host_group=[a.display for a in self.agents],
                               adversary=self.adversary.display if self.adversary else '', jitter=self.jitter,
                               source=self.source.display if self.source else '',
                               planner=self.planner.name if self.planner else '',
                               start=self.start.strftime('%Y-%m-%d %H:%M:%S') if self.start else '',
                               state=self.state, phase=self.phase, obfuscator=self.obfuscator,
                               autonomous=self.autonomous, finish=self.finish,
                               chain=[lnk.display for lnk in self.chain]))

    @property
    def states(self):
        return dict(RUNNING='running',
                    RUN_ONE_LINK='run_one_link',
                    PAUSED='paused',
                    OUT_OF_TIME='out_of_time',
                    FINISHED='finished')

    def __init__(self, name, agents, adversary, id=None, jitter='2/8', source=None, planner=None, state='running',
                 autonomous=True, phases_enabled=True, obfuscator='plain-text', group=None, auto_close=True,
                 visibility=50, access=None):
        super().__init__()
        self.id = id
        self.start, self.finish = None, None
        self.name = name
        self.group = group
        self.agents = agents
        self.adversary = adversary
        self.jitter = jitter
        self.source = source
        self.planner = planner
        self.state = state
        self.autonomous = autonomous
        self.phases_enabled = phases_enabled
        self.phase = 0
        self.obfuscator = obfuscator
        self.auto_close = auto_close
        self.visibility = visibility
        self.chain, self.rules = [], []
        self.access = access if access else self.Access.APP
        if source:
            self.rules = source.rules

    def store(self, ram):
        existing = self.retrieve(ram['operations'], self.unique)
        if not existing:
            ram['operations'].append(self)
            return self.retrieve(ram['operations'], self.unique)
        return existing

    def set_start_details(self):
        self.id = self.id if self.id else randint(0, 999999)
        self.start = datetime.now()

    def add_link(self, link):
        self.chain.append(link)

    def all_facts(self):
        seeded_facts = [f for f in self.source.facts] if self.source else []
        learned_facts = [f for lnk in self.chain for f in lnk.facts if f.score > 0]
        return seeded_facts + learned_facts

    def has_fact(self, trait, value):
        for f in self.all_facts():
            if f.trait == trait and f.value == value:
                return True
        return False

    def all_relationships(self):
        return [r for lnk in self.chain for r in lnk.relationships]

    async def apply(self, link):
        while self.state != self.states['RUNNING']:
            if self.state == self.states['RUN_ONE_LINK']:
                self.add_link(link)
                self.state = self.states['PAUSED']
                return link.id
            else:
                await asyncio.sleep(15)
        self.add_link(link)
        return link.id

    async def close(self):
        if self.state not in [self.states['FINISHED'], self.states['OUT_OF_TIME']]:
            self.state = self.states['FINISHED']
        self.finish = self.get_current_timestamp()

    async def wait_for_phase_completion(self):
        for member in self.agents:
            if not member.trusted:
                for link in await self._unfinished_links_for_agent(member.paw):
                    link.status = link.states['UNTRUSTED']
                continue
            while len(await self._unfinished_links_for_agent(member.paw)) > 0:
                await asyncio.sleep(3)
                if not member.trusted:
                    break

    async def wait_for_links_completion(self, link_ids):
        """
        Wait for started links to be completed
        :param link_ids:
        :return: None
        """
        for link_id in link_ids:
            link = [link for link in self.chain if link.id == link_id][0]
            member = [member for member in self.agents if member.paw == link.paw][0]
            while not link.finish or link.can_ignore():
                await asyncio.sleep(5)
                if not member.trusted:
                    break

    async def is_closeable(self):
        if await self.is_finished() or (self.auto_close and self.phase >= len(self.adversary.phases)):
            self.state = self.states['FINISHED']
            return True
        return False

    async def is_finished(self):
        if self.state in [self.states['FINISHED'], self.states['OUT_OF_TIME']]:
            return True
        return False

    def link_status(self):
        return -3 if self.autonomous else -1

    async def active_agents(self):
        active = []
        for agent in self.agents:
            if agent.last_seen > self.start:
                active.append(agent)
        return active

    def report(self, file_svc, output=False, redacted=False):
        report = dict(name=self.name, host_group=[a.display for a in self.agents],
                      start=self.start.strftime('%Y-%m-%d %H:%M:%S'),
                      steps=[], finish=self.finish, planner=self.planner.name, adversary=self.adversary.display,
                      jitter=self.jitter, facts=[f.display for f in self.all_facts()])
        agents_steps = {a.paw: {'steps': []} for a in self.agents}
        for step in self.chain:
            step_report = dict(ability_id=step.ability.ability_id,
                               command=step.command,
                               delegated=step.decide.strftime('%Y-%m-%d %H:%M:%S'),
                               run=step.finish,
                               status=step.status,
                               platform=step.ability.platform,
                               executor=step.ability.executor,
                               pid=step.pid,
                               description=step.ability.description,
                               name=step.ability.name,
                               attack=dict(tactic=step.ability.tactic,
                                           technique_name=step.ability.technique_name,
                                           technique_id=step.ability.technique_id))
            if output and step.output:
                step_report['output'] = self.decode_bytes(file_svc.read_result_file(step.unique))
            agents_steps[step.paw]['steps'].append(step_report)
        report['steps'] = agents_steps
        report['skipped_abilities'] = self._get_skipped_abilities_by_agent()
        if redacted:
            return redact_report(report)
        return report

    async def run(self, services):
        try:
            planner = await self._get_planning_module(services)
            self.adversary = await self._adjust_adversary_phases()
            await self._run_phases(planner)

            self.phases_enabled = False
            while not await self.is_closeable():
                await asyncio.sleep(10)
                await self._run_phases(planner)
            await self._cleanup_operation(services)
            await self.close()
            await self._save_new_source(services)
        except Exception as e:
            logging.error(e, exc_info=True)

    """ PRIVATE """

    async def _run_phases(self, planner):
        for phase in self.adversary.phases:
            if not await self.is_closeable():
                await planner.execute(phase)
                if planner.stopping_condition_met:
                    break
                await self.wait_for_phase_completion()
            self.phase = phase

    async def _cleanup_operation(self, services):
        for member in self.agents:
            for link in await services.get('planning_svc').get_cleanup_links(self, member):
                self.add_link(link)
        await self.wait_for_phase_completion()

    async def _get_planning_module(self, services):
        planning_module = import_module(self.planner.module)
        planner_params = ast.literal_eval(self.planner.params)
        return getattr(planning_module, 'LogicalPlanner')(self, services.get('planning_svc'), **planner_params,
                                                          stopping_conditions=self.planner.stopping_conditions)

    async def _adjust_adversary_phases(self):
        if not self.phases_enabled:
            return Adversary(adversary_id=(self.adversary.adversary_id + "_phases_disabled"),
                             name=(self.adversary.name + " - with phases disabled"),
                             description=(self.adversary.name + " with phases disabled"),
                             phases={1: [i for phase, ab in self.adversary.phases.items() for i in ab]})
        else:
            return self.adversary

    async def _save_new_source(self, services):
        data = dict(
            id=str(uuid.uuid4()),
            name=self.name,
            facts=[dict(trait=f.trait, value=f.value, score=f.score) for link in self.chain for f in link.facts]
        )
        await services.get('rest_svc').persist_source(data)

    async def update_operation(self, services):
        self.agents = await services.get('rest_svc').construct_agents_for_group(self.group)

    async def _unfinished_links_for_agent(self, paw):
        return [l for l in self.chain if l.paw == paw and not l.finish and not l.can_ignore()]

    def _get_skipped_abilities_by_agent(self):
        abilities_by_agent = self._get_all_possible_abilities_by_agent()
        skipped_abilities = []
        for agent in self.agents:
            agent_skipped = defaultdict(dict)
            agent_executors = agent.executors
            agent_ran = set([link.ability.display['ability_id'] for link in self.chain if link.paw == agent.paw])
            for ab in abilities_by_agent[agent.paw]['all_abilities']:
                skipped = self._check_reason_skipped(agent=agent, ability=ab, agent_executors=agent_executors,
                                                     op_facts=[f.display for f in self.all_facts()],
                                                     state=self.state, agent_ran=agent_ran)
                if skipped:
                    if agent_skipped[skipped['ability_id']]:
                        if agent_skipped[skipped['ability_id']]['reason_id'] < skipped['reason_id']:
                            agent_skipped[skipped['ability_id']] = skipped
                    else:
                        agent_skipped[skipped['ability_id']] = skipped
            skipped_abilities.append({agent.paw: list(agent_skipped.values())})
        return skipped_abilities

    def _get_all_possible_abilities_by_agent(self):
        return {a.paw: {'all_abilities': [ab for p in self.adversary.phases
                                          for ab in self.adversary.phases[p]]} for a in self.agents}

    def _check_reason_skipped(self, agent, ability, op_facts, state, agent_executors, agent_ran):
        variables = re.findall(r'#{(.*?)}', self.decode_bytes(ability.test), flags=re.DOTALL)
        if ability.ability_id in agent_ran:
            return
        elif not agent.trusted:
            return dict(reason='Agent untrusted', reason_id=self.Reason.UNTRUSTED.value,
                        ability_id=ability.ability_id, ability_name=ability.name)
        elif ability.platform != agent.platform:
            return dict(reason='Wrong platform', reason_id=self.Reason.PLATFORM.value, ability_id=ability.ability_id,
                        ability_name=ability.name)
        elif ability.executor not in agent_executors:
            return dict(reason='Executor not available', reason_id=self.Reason.EXECUTOR.value,
                        ability_id=ability.ability_id, ability_name=ability.name)
        elif variables and not all(op_fact in op_facts for op_fact in variables):
            return dict(reason='Fact dependency not fulfilled', reason_id=self.Reason.FACT_DEPENDENCY.value,
                        ability_id=ability.ability_id, ability_name=ability.name)
        elif ability.privilege != agent.privilege:
            return dict(reason='Ability privilege not fulfilled', reason_id=self.Reason.PRIVILEGE.value,
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

    class Reason(Enum):
        PLATFORM = 0
        EXECUTOR = 1
        FACT_DEPENDENCY = 2
        PRIVILEGE = 3
        OP_RUNNING = 4
        UNTRUSTED = 5
