import copy
import itertools
import re
from base64 import b64decode
from datetime import datetime
from importlib import import_module

from app.service.base_service import BaseService
from app.utility.rule import RuleSet


class PlanningService(BaseService):

    def __init__(self):
        self.log = self.add_service('planning_svc', self)

    async def get_links(self, operation, agent, phase=None, trim=False):
        """
        For an operation, phase and agent combination, determine which (potential) links can be executed
        :param operation:
        :param agent:
        :param phase:
        :param trim: call trim_links() call on list of links before returning
        :return: a list of links
        """
        await self.get_service('parsing_svc').parse_facts(operation)
        operation = (await self.get_service('data_svc').explode_operation(criteria=dict(id=operation['id'])))[0]

        if (not agent['trusted']) and (not operation['allow_untrusted']):
            self.log.debug('Agent %s untrusted: no link created' % agent['paw'])
            return []

        if phase:
            abilities = [i for p, v in operation['adversary']['phases'].items() if p <= phase for i in v]
        else:
            abilities = [i for p, v in operation['adversary']['phases'].items() for i in v]
    
        abilities = sorted(abilities, key=lambda i: i['id'])
        link_status = await self._default_link_status(operation)
        links = []
        for a in await self.get_service('agent_svc').capable_agent_abilities(abilities, agent):
            links.append(await self.craft_link(operation, agent, a))
        if trim:
            ability_requirements = {ab['id']: ab.get('requirements', []) for ab in abilities}
            links[:] = await self.trim_links(operation, links, agent, ability_requirements)
        return await self._sort_links(links)

    async def get_cleanup_links(self, operation, agent):
        """
        For a given operation, select all cleanup links
        :param operation:
        :param agent
        :return: None
        """
        link_status = await self._default_link_status(operation)
        if (not agent['trusted']) and (not operation['allow_untrusted']):
            self.log.debug('Agent %s untrusted: no cleanup-link created' % agent['paw'])
            return
        links = []
        for link in await self.get_service('data_svc').explode_chain(criteria=dict(paw=agent['paw'],
                                                                                   op_id=operation['id'])):
            ability = (await self.get_service('data_svc').explode_abilities(criteria=dict(id=link['ability'])))[0]
            if ability['cleanup'] and link['status'] >= 0:
                links.append(craft_link(operation, agent, ability, dict(cleanup=1, jitter=0)))
        return reversed(await self._trim_links(operation, links, agent))
        
    async def craft_link(self, operation, agent, ability, fields):
        """
        TODO: docs
        """
        # craft link based on default operation, agent and ability values
        link = dict(op_id=operation['id'], paw=agent['paw'], ability=ability['id'],
                    command=ability['test'], executor=ability['executor'], score=0,
                    jitter=self.jitter(operation["jitter"]), decide=datetime.now(),
                    status=await self._default_link_status(operation),
                    adversary_map_id=ability["adversary_map_id"])

        # if caller further specifies modified link fields, update link
        link.update(fields)

        return link

    async def trim_links(self, operation, links, agent, ability_requirements=None):
        """
        Trim links in supplied list. Where 'trim' entails:
            - adding all possible test variants
            - removing completed links (i.e. agent has already completed)
            - removing links that did not have template fact variables replaced by fact values
        
        :param operation:
        :param links:
        :param agent:
        :return: trimmed list of links
        """
        links[:] = await self.add_test_variants(links, agent, operation, ability_requirements)
        links = await self.remove_completed_links(operation, links, agent)
        links = await self.remove_links_missing_facts(links)
        self.log.debug('Created %d links for %s' % (len(links), agent['paw']))
        return links

    async def add_test_variants(self, links, agent, operation, ability_requirements=None):
        """
        Create a list of all possible links for a given phase
        """
        group = agent['host_group']
        for link in links:
            decoded_test = self.decode(link['command'], agent, group)
            variables = re.findall(r'#{(.*?)}', decoded_test, flags=re.DOTALL)
            if variables:
                agent_facts = await self._get_agent_facts(operation['id'], agent['paw'])
                relevant_facts = await self._build_relevant_facts(variables, operation.get('facts', []), agent_facts)
                valid_facts = await RuleSet(rules=operation.get('rules', [])).apply_rules(facts=relevant_facts[0])
                for combo in list(itertools.product(*valid_facts)):
                    if ability_requirements and not await self._do_enforcements(ability_requirements[link['ability']], operation, link, combo):
                        continue
                    copy_test = copy.deepcopy(decoded_test)
                    copy_link = copy.deepcopy(link)
                    variant, score, used = await self._build_single_test_variant(copy_test, combo)
                    copy_link['command'] = self.encode_string(variant)
                    copy_link['score'] = score
                    copy_link['used'] = used
                    links.append(copy_link)
            else:
                link['command'] = self.encode_string(decoded_test)
        return links

    async def remove_completed_links(self, operation, links, agent):
        """
        Remove any links that have already been completed by the operation for the agent
        :param operation:
        :param links:
        :param agent:
        :return: updated list of links
        """
        completed_links = [l['command'] for l in operation['chain'] if l['paw'] == agent['paw'] and (l["finish"] or l["status"] == self.LinkState.DISCARD.value)]
        links[:] = [l for l in links if l["command"] not in completed_links]
        return links

    async def remove_links_missing_facts(self, links):
        """
        Remove any links that did not have facts encoded into command
        :param links:
        :return: updated list of links
        """
        links[:] = [l for l in links if
                    not re.findall(r'#{(.*?)}', b64decode(l['command']).decode('utf-8'), flags=re.DOTALL)]
        return links

    @staticmethod
    async def capable_agent_abilities(phase_abilities, agent):
        """
        TODO: docs
        """
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
        Sort links by their score then by the order they are defined in an adversary profile
        """
        return sorted(links, key=lambda k: (-k['score'], k['adversary_map_id']))

    @staticmethod
    def _reward_fact_relationship(combo_set, combo_link, score):
        if len(combo_set) == 1 and len(combo_link) == 1:
            score *= 2
        return score

    async def _do_enforcements(self, ability_requirements, operation, link, combo):
        for requirements_info in ability_requirements:
            uf = link.get('used', [])
            requirement = await self.load_module('Requirement', requirements_info)
            if not requirement.enforce(combo[0], uf, operation['facts']):
                return False
        return True

    @staticmethod
    def _is_fact_bound(fact):
        return not fact['link_id']

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

    @staticmethod
    async def _build_single_test_variant(copy_test, combo):
        """
        Replace all variables with facts from the combo to build a single test variant
        """
        score, used = 0, list()
        for var in combo:
            score += (score + var['score'])
            used.append(var['id'])
            copy_test = copy_test.replace('#{%s}' % var['property'], var['value'])
        return copy_test, score, used

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

    async def _default_link_status(self, operation):
        return self.LinkState.EXECUTE.value if operation['autonomous'] else self.LinkState.PAUSE.value
