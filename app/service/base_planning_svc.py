import copy
import itertools
import re
from base64 import b64decode

from app.service.base_service import BaseService
from app.utility.rule import RuleSet


class BasePlanningService(BaseService):

    async def trim_links(self, operation, agent, links, ability_requirements=None):
        """
        Trim links in supplied list. Where 'trim' entails:
            - adding all possible test variants
            - removing completed links (i.e. agent has already completed)
            - removing links that did not have template fact variables replaced by fact values
        
        :param operation:
        :param links:
        :param agent: C_agent #TODO fill
        :return: trimmed list of links
        """
        links[:] = await self.add_test_variants(operation, agent, links, ability_requirements)
        links = await self.remove_completed_links(operation, agent, links)
        links = await self.remove_links_missing_facts(links)
        self.log.debug('Created %d links for %s' % (len(links), agent.paw))
        return links

    async def add_test_variants(self, operation, agent, links, ability_requirements=None):
        """
        Create a list of all possible links for a given phase
        :param operation:
        :param agent: C_agent #TODO
        :param links:
        :param ability_requirements:
        return: list of links, with additional variant links
        """
        group = agent.group
        for link in links:
            decoded_test = self.decode(link['command'], agent, group)
            variables = re.findall(r'#{(.*?)}', decoded_test, flags=re.DOTALL)
            if variables:
                agent_facts = await self._get_agent_facts(operation['id'], agent.paw)
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

    async def remove_completed_links(self, operation, agent, links):
        """
        Remove any links that have already been completed by the operation for the agent
        :param operation:
        :param links:
        :param agent:
        :return: updated list of links
        """
        completed_links = [l['command'] for l in operation['chain'] if l['paw'] == agent.paw and (l["finish"] or l["status"] == self.LinkState.DISCARD.value)]
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

    """ PRIVATE """

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

    async def _do_enforcements(self, ability_requirements, operation, link, combo):
        for requirements_info in ability_requirements:
            uf = link.get('used', [])
            requirement = await self.load_module('Requirement', requirements_info)
            if not requirement.enforce(combo[0], uf, operation['facts']):
                return False
        return True