import ast
import asyncio
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime
from enum import Enum
from importlib import import_module
from random import randint

from app.utility.base_object import BaseObject


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
                               state=self.state, obfuscator=self.obfuscator,
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
                 autonomous=True, atomic_enabled=False, obfuscator='plain-text', group=None, auto_close=True,
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
        self.atomic_enabled = atomic_enabled
        self.last_ran = None
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

    async def close(self, services):
        await self._cleanup_operation(services)
        await self._save_new_source(services)
        if self.state not in [self.states['FINISHED'], self.states['OUT_OF_TIME']]:
            self.state = self.states['FINISHED']
        self.finish = self.get_current_timestamp()

    async def wait_for_completion(self):
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
        if await self.is_finished() or self.auto_close and self._is_atomic_closeable():
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

    async def get_active_agent_by_paw(self, paw):
        return [a for a in await self.active_agents() if a.paw == paw]

    def report(self, file_svc, output=False, redacted=False):
        try:
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

            return report
        except Exception:
            logging.error('Error saving operation report (%s)' % self.name)

    async def run(self, services):
        try:
            planner = await self._get_planning_module(services)
            await self._run(planner)

            self.atomic_enabled = False
            while not await self.is_closeable():
                await asyncio.sleep(10)
                await self._run(planner)
            await self.close(services)
        except Exception as e:
            logging.error(e, exc_info=True)

    """ PRIVATE """

    async def _run(self, planner):
        ability_set_format = self._get_ability_set_format_for_planner()
        for ability in ability_set_format:
            if not await self.is_closeable():
                await planner.execute(ability_set_format.index(ability))
                if planner.stopping_condition_met:
                    break
                await self.wait_for_completion()
            self.last_ran = ability

    async def _cleanup_operation(self, services):
        for member in self.agents:
            for link in await services.get('planning_svc').get_cleanup_links(self, member):
                self.add_link(link)
        await self.wait_for_completion()

    async def _get_planning_module(self, services):
        planning_module = import_module(self.planner.module)
        planner_params = ast.literal_eval(self.planner.params)
        return planning_module.LogicalPlanner(self, services.get('planning_svc'), **planner_params,
                                              stopping_conditions=self.planner.stopping_conditions)

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

    def _is_atomic_closeable(self):
        return self.atomic_enabled and self.last_ran == self.adversary.atomic_ordering[-1]

    def _get_ability_set_format_for_planner(self):
        if not self.atomic_enabled:
            return [self.adversary.atomic_ordering]
        return self.adversary.atomic_ordering

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
        return {a.paw: {'all_abilities': self.adversary.atomic_ordering} for a in self.agents}

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
        elif not agent.privileged_to_run(ability):
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
