import asyncio
import copy
import itertools
import re
from base64 import b64decode
from datetime import datetime
from enum import Enum

from app.service.base_service import BaseService


class PlanningService(BaseService):

    def __init__(self):
        self.log = self.add_service('planning_svc', self)

    async def select_links(self, operation, agent, phase):
        """
        For an operation, phase and agent combination, determine which potential links can be executed
        :param operation:
        :param agent:
        :param phase:
        :return: a list of links
        """
        await self.get_service('parsing_svc').parse_facts(operation)
        operation = (await self.get_service('data_svc').explode_operation(criteria=dict(id=operation['id'])))[0]

        if (not agent['trusted']) and (not operation['allow_untrusted']):
            self.log.debug('Agent %s untrusted: no link created' % agent['paw'])
            return []
        phase_abilities = [i for p, v in operation['adversary']['phases'].items() if p <= phase for i in v]
        phase_abilities = sorted(phase_abilities, key=lambda i: i['id'])
        link_status = await self._default_link_status(operation)

        links = []
        for a in await self.capable_agent_abilities(phase_abilities, agent):
            links.append(
                dict(op_id=operation['id'], paw=agent['paw'], ability=a['id'], command=a['test'], score=0,
                     status=link_status, decide=datetime.now(), executor=a['executor'],
                     jitter=self.jitter(operation['jitter']), adversary_map_id=a['adversary_map_id']))
        links[:] = await self._trim_links(operation, links, agent)
        return await self._sort_links(links)

    async def create_cleanup_links(self, operation):
        """
        For a given operation, create a link for every cleanup action on every executed ability
        :param operation:
        :return: None
        """
        op = (await self.get_service('data_svc').explode_operation(criteria=dict(id=operation['id'])))[0]
        link_status = await self._default_link_status(op)
        for member in op['host_group']:
            if (not member['trusted']) and (not op['allow_untrusted']):
                self.log.debug('Agent %s untrusted: no cleanup-link created' % member['paw'])
                continue
            links = []
            for link in await self.get_service('data_svc').explode_chain(criteria=dict(paw=member['paw'],
                                                                                       op_id=op['id'])):
                ability = (await self.get_service('data_svc').explode_abilities(criteria=dict(id=link['ability'])))[0]
                if ability['cleanup'] and link['status'] >= 0:
                    links.append(dict(op_id=op['id'], paw=member['paw'], ability=ability['id'], cleanup=1,
                                      command=ability['cleanup'], executor=ability['executor'], score=0, jitter=0,
                                      decide=datetime.now(), status=link_status))
            links[:] = await self._trim_links(op, links, member)
            for link in reversed(links):
                link.pop('rewards', [])
                await self.get_service('data_svc').create('core_chain', link)
        await self.wait_for_phase(op)

    async def wait_for_phase(self, operation):
        """
        Wait for all started links to be completed
        :param operation:
        :return: None
        """
        for member in operation['host_group']:
            if (not member['trusted']) and (not operation['allow_untrusted']):
                continue
            op = await self.get_service('data_svc').explode_operation(criteria=dict(id=operation['id']))
            while next((True for lnk in op[0]['chain'] if lnk['paw'] == member['paw'] and not lnk['finish'] and not lnk['status'] == self.LinkState.DISCARD.value),
                       False):
                await asyncio.sleep(3)
                if await self._trust_issues(operation, member['paw']):
                    break
                op = await self.get_service('data_svc').explode_operation(criteria=dict(id=operation['id']))

    async def decode(self, encoded_cmd, agent, group):
        """
        Replace all global variables in a command with the values associated to a specific agent
        :param encoded_cmd:
        :param agent:
        :param group:
        :return: the updated command string
        """
        decoded_cmd = self.decode_bytes(encoded_cmd)
        decoded_cmd = decoded_cmd.replace('#{server}', agent['server'])
        decoded_cmd = decoded_cmd.replace('#{group}', group)
        decoded_cmd = decoded_cmd.replace('#{paw}', agent['paw'])
        decoded_cmd = decoded_cmd.replace('#{location}', agent['location'])
        return decoded_cmd

    @staticmethod
    async def capable_agent_abilities(phase_abilities, agent):
        abilities = []
        preferred = next((e['executor'] for e in agent['executors'] if e['preferred']))
        executors = [e['executor'] for e in agent['executors']]
        for ai in set([pa['ability_id'] for pa in phase_abilities]):
            total_ability = [ab for ab in phase_abilities if (ab['ability_id'] == ai)
                             and (ab['platform'] == agent['platform']) and (ab['executor'] in executors)]
            if len(total_ability) > 0:
                val = next((ta for ta in total_ability if ta['executor'] == preferred), total_ability[0])
                abilities.append(val)
        return abilities

    """ PRIVATE """

    @staticmethod
    async def _sort_links(links):
        """
        sort links by their score then by the order they are defined in an adversary profile
        """
        return sorted(links, key=lambda k: (-k['score'], k['adversary_map_id']))

    async def _trim_links(self, operation, links, agent):
        host_already_ran = [l['command'] for l in operation['chain'] if l['paw'] == agent['paw']]
        links[:] = await self._add_test_variants(links, agent, operation)
        links[:] = [l for l in links if l['command'] not in host_already_ran]
        links[:] = [l for l in links if
                    not re.findall(r'#{(.*?)}', b64decode(l['command']).decode('utf-8'), flags=re.DOTALL)]
        self.log.debug('Created %d links for %s' % (len(links), agent['paw']))
        return links

    async def _add_test_variants(self, links, agent, operation):
        """
        Create a list of all possible links for a given phase
        """
        group = agent['host_group']
        for link in links:
            decoded_test = await self.decode(link['command'], agent, group)
            variables = re.findall(r'#{(.*?)}', decoded_test, flags=re.DOTALL)
            if variables:
                agent_facts = await self._get_agent_facts(operation['id'], agent['paw'])
                relevant_facts = await self._build_relevant_facts(variables, operation.get('facts', []), agent_facts)
                valid_facts = await self._apply_rules(rules=operation.get('rules', []), facts=relevant_facts)
                for combo in list(itertools.product(*valid_facts)):
                    copy_test = copy.deepcopy(decoded_test)
                    copy_link = copy.deepcopy(link)

                    variant, score, rewards = await self._build_single_test_variant(copy_test, combo)
                    copy_link['command'] = self.encode_string(variant)
                    copy_link['score'] = score
                    copy_link['rewards'] = rewards
                    links.append(copy_link)
            else:
                link['command'] = self.encode_string(decoded_test)
        return links

    @staticmethod
    def _is_fact_bound(fact):
        return not fact['link_id']

    async def _apply_rules(self, rules, facts):
        valid_facts = []
        if len(rules):
            for fact in facts[0]:
                if await self._is_fact_allowed(rules, fact):
                    valid_facts.append(fact)
        return [valid_facts]

    @staticmethod
    async def _is_fact_allowed(rules, fact):
        allowed = True
        for rule in rules.get(fact['property'], []):
            if re.match(rule.get('match', '.*'), fact['value']):
                if rule['action'] == RuleAction.DENY.value:
                    allowed = False
                elif rule['action'] == RuleAction.ALLOW.value:
                    allowed = True
        return allowed

    async def _build_relevant_facts(self, variables, facts, agent_facts):
        """
        Create a list of ([fact, value, score]) tuples for each variable/fact
        """
        facts = [f for f in facts if f['score'] > 0]
        relevant_facts = []
        for v in variables:
            variable_facts = []
            for fact in [f for f in facts if f['property'] == v]:
                if fact['property'].startswith('host'):
                    if fact['id'] in agent_facts or self._is_fact_bound(fact):
                        variable_facts.append(fact)
                else:
                    variable_facts.append(fact)
            relevant_facts.append(variable_facts)
        return relevant_facts

    async def _build_single_test_variant(self, copy_test, combo):
        """
        Replace all variables with facts from the combo to build a single test variant
        """
        score, rewards = 0, list()
        for var in combo:
            score += (score + var['score'])
            rewards.append(var['id'])
            copy_test = copy_test.replace('#{%s}' % var['property'], var['value'])
        return copy_test, score, rewards

    async def _get_agent_facts(self, op_id, paw):
        """
        Collect a list of this agent's facts
        """
        agent_facts = []
        for link in await self.get_service('data_svc').dao.get('core_chain', criteria=dict(op_id=op_id, paw=paw)):
            facts = await self.get_service('data_svc').dao.get('core_fact', criteria=dict(link_id=link['id']))
            for f in facts:
                agent_facts.append(f['id'])
        return agent_facts

    async def _trust_issues(self, operation, paw):
        if not operation['allow_untrusted']:
            agent = await self.get_service('data_svc').explode_agents(criteria=dict(paw=paw))
            return not agent[0]['trusted']
        return False

    async def _default_link_status(self, operation):
        return self.LinkState.EXECUTE.value if operation['autonomous'] else self.LinkState.PAUSE.value


class RuleAction(Enum):
    ALLOW = 1
    DENY = 0
