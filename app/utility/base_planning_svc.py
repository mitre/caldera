import copy
import itertools
import re
from base64 import b64decode

from app.utility.base_service import BaseService
from app.utility.rule import RuleSet


class BasePlanningService(BaseService):

    async def trim_links(self, operation, links, agent):
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
        links[:] = await self.add_test_variants(links, agent, operation)
        links = await self.remove_completed_links(operation, agent, links)
        links = await self.remove_links_missing_facts(links)
        links = await self.remove_links_missing_requirements(links, operation)
        links = await self.remove_links_duplicate_hosts(links, operation)
        self.log.debug('Created %d links for %s' % (len(links), agent.paw))
        return links

    async def add_test_variants(self, links, agent, operation):
        """
        Create a list of all possible links for a given phase
        :param links:
        :param agent:
        :param operation:
        :return: updated list of links
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
                    copy_test = copy.deepcopy(decoded_test)
                    copy_link = copy.deepcopy(link)
                    variant, score, used = await self._build_single_test_variant(copy_test, combo)
                    copy_link.command = self.encode_string(variant)
                    copy_link.score = score
                    copy_link.used.extend(used)
                    links.append(copy_link)
            else:
                link.command = self.encode_string(decoded_test)
        return links

    @staticmethod
    async def remove_completed_links(operation, agent, links):
        """
        Remove any links that have already been completed by the operation for the agent
        :param operation:
        :param links:
        :param agent:
        :return: updated list of links
        """
        completed_links = [l.command for l in operation.chain
                           if l.paw == agent.paw and (l.finish or l.status == l.states["DISCARD"])]
        links[:] = [l for l in links if l.command not in completed_links]
        return links

    @staticmethod
    async def remove_links_missing_facts(links):
        """
        Remove any links that did not have facts encoded into command
        :param links:
        :return: updated list of links
        """
        links[:] = [l for l in links if
                    not re.findall(r'#{(.*?)}', b64decode(l.command).decode('utf-8'), flags=re.DOTALL)]
        return links

    async def remove_links_missing_requirements(self, links, operation):
        relationships = operation.all_relationships()
        links[:] = [l for l in links if await self._do_enforcements(l, relationships)]
        return links

    async def remove_links_duplicate_hosts(self, links ,operation):
        relationships = operation.all_relationships()
        links[:] = [l for l in links if await self._exclude_existing(l, operation)]
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
            copy_test = copy_test.replace('#{%s}' % var.trait, var.value.strip())
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
        """
        get facts for given agent
        """
        agent_facts = []
        for link in [l for l in operation.chain if l.paw == paw]:
            for f in link.facts:
                agent_facts.append(f.unique)
        return agent_facts

    async def _do_enforcements(self, link, relationships):
        """
        enforce any defined requirements on the link
        """
        for req_inst in link.ability.requirements:
            requirements_info = dict(module=req_inst.module, enforcements=req_inst.relationships[0])
            requirement = await self.load_module('Requirement', requirements_info)
            if not requirement.enforce(link.used, relationships):
                return False
        return True

    async def _exclude_existing(self, link, operation):
        all_hostnames = [agent.paw.split('$')[0].lower() for agent in await operation._active_agents()]
        for item in link.relationships:
            # prevent backwards lateral movement
            if 'remote.host' in item.trait:
                if item.value.split('.')[0].lower() in all_hostnames:
                    return False
                elif any(h in item.value.split('.')[0].lower() for h in all_hostnames):
                    return False
        return True