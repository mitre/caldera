import copy
import itertools
import re
from base64 import b64decode

from app.utility.base_service import BaseService
from app.utility.rule import RuleSet


class BasePlanningService(BaseService):

    async def trim_links(self, operation, links, agent, ability_requirements=None):
        """
        Trim links in supplied list. Where 'trim' entails:
            - adding all possible test variants
            - removing completed links (i.e. agent has already completed)
            - removing links that did not have template fact variables replaced by fact values
        
        :param operation:
        :param links:
        :param agent: C_agent
        :return: trimmed list of links
        """
        links[:] = await self.add_test_variants(links, agent, operation, ability_requirements)
        links = await self.remove_completed_links(operation, agent, links)
        links = await self.remove_links_missing_facts(links)
        self.log.debug('Created %d links for %s' % (len(links), agent.paw))
        return links

    async def add_test_variants(self, links, agent, operation, ability_requirements=None):
        """
        Create a list of all possible links for a given phase
        """
        group = agent.group
        for link in links:
            decoded_test = self.decode(link.command, agent, group)
            variables = re.findall(r'#{(.*?)}', decoded_test, flags=re.DOTALL)
            if variables:
                agent_facts = await self._get_agent_facts(operation, agent.paw)
                relevant_facts = await self._build_relevant_facts(variables, operation, agent_facts)
                valid_facts = await RuleSet(rules=operation.rules).apply_rules(facts=relevant_facts[0])
                for combo in list(itertools.product(*valid_facts)):
                    if ability_requirements and not await self._do_enforcements(ability_requirements[link.ability.unique], operation, link, combo):
                        continue
                    copy_test = copy.deepcopy(decoded_test)
                    copy_link = copy.deepcopy(link)
                    variant, score, used = await self._build_single_test_variant(copy_test, combo)
                    copy_link.command = self.encode_string(variant)
                    copy_link.score = score
                    copy_link.used = used
                    links.append(copy_link)
            else:
                link.command = self.encode_string(decoded_test)
        return links

    async def remove_completed_links(self, operation, agent, links):
        """
        Remove any links that have already been completed by the operation for the agent
        :param operation:
        :param links:
        :param agent:
        :return: updated list of links
        """
        completed_links = [l.command for l in operation.chain if l.paw == agent.paw and (l.finish or l.status == self.LinkState.DISCARD.value)]
        links[:] = [l for l in links if l.command not in completed_links]
        return links

    async def remove_links_missing_facts(self, links):
        """
        Remove any links that did not have facts encoded into command
        :param links:
        :return: updated list of links
        """
        links[:] = [l for l in links if
                    not re.findall(r'#{(.*?)}', b64decode(l.command).decode('utf-8'), flags=re.DOTALL)]
        return links

    """ PRIVATE """

    @staticmethod
    async def _build_single_test_variant(copy_test, combo):
        """
        Replace all variables with facts from the combo to build a single test variant
        """
        score, used = 0, list()
        for var in combo:
            score += (score + var.score)
            used.append(var)
            copy_test = copy_test.replace('#{%s}' % var.trait, var.value)
        return copy_test, score, used

    @staticmethod
    def _is_fact_bound(fact):
        return not fact['link_id']

    @staticmethod
    async def _build_relevant_facts(variables, operation, agent_facts):
        """
        Create a list of ([fact, value, score]) tuples for each variable/fact
        """
        facts = operation.all_facts()

        relevant_facts = []
        for v in variables:
            variable_facts = []
            for fact in [f for f in facts if f.trait == v]:
                if fact.trait.startswith('host'):
                    if fact.unique in agent_facts:
                        variable_facts.append(fact)
                else:
                    variable_facts.append(fact)
            relevant_facts.append(variable_facts)
        return relevant_facts

    @staticmethod
    async def _get_agent_facts(operation, paw):
        agent_facts = []
        for link in [l for l in operation.chain if l.paw == paw]:
            for f in link.facts:
                agent_facts.append(f.unique)
        return agent_facts

    async def _do_enforcements(self, ability_requirements, operation, link, combo):
        for req_inst in ability_requirements:
            uf = link.get('used', [])
            requirements_info = dict(module=req_inst.module, enforcements=req_inst.relationships[0])
            requirement = await self.load_module('Requirement', requirements_info)
            if not requirement.enforce(combo[0], uf, operation.facts):
                return False
        return True