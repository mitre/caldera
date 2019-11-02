import copy
import itertools
import re
from base64 import b64decode

from app.objects.c_link import Link
from app.service.base_service import BaseService
from app.utility.rule import RuleSet


class PlanningService(BaseService):

    def __init__(self):
        self.log = self.add_service('planning_svc', self)

    async def select_links(self, operation, agent, phase):
        """
        For an operation, phase and agent combination, determine which (potential) links can be executed
        :param operation:
        :param agent:
        :param phase:
        :return: a list of links
        """
        if (not agent.trusted) and (not operation.allow_untrusted):
            self.log.debug('Agent %s untrusted: no link created' % agent.paw)
            return []
        phase_abilities = [i for p, v in operation.adversary.phases.items() if p <= phase for i in v]
        link_status = await self._default_link_status(operation)

        links = []
        for a in await agent.capabilities(phase_abilities):
            links.append(
                Link(operation=operation.name, command=a.test, paw=agent.paw, score=0, ability=a,
                     status=link_status, jitter=self.jitter(operation.jitter))
            )
        ability_requirements = {ab.unique: ab.requirements for ab in phase_abilities}
        links[:] = await self._trim_links(operation, links, agent, ability_requirements)
        return await self._sort_links(links)

    async def select_cleanup_links(self, operation, agent):
        """
        For a given operation, select all cleanup links
        :param operation:
        :param agent:
        :return: None
        """
        link_status = await self._default_link_status(operation)
        if (not agent.trusted) and (not operation.allow_untrusted):
            self.log.debug('Agent %s untrusted: no cleanup-link created' % agent.paw)
            return
        links = []
        for link in [l for l in operation.chain if l.paw == agent.paw]:
            ability = (await self.get_service('data_svc').locate('abilities', match=dict(unique=link.ability.unique)))[0]
            if ability.cleanup and link.status >= 0:
                links.append(Link(operation=operation.name, command=ability.cleanup, paw=agent.paw, cleanup=1,
                                  ability=ability, score=0, jitter=0, status=link_status))
        return reversed(await self._trim_links(operation, links, agent))

    """ PRIVATE """

    @staticmethod
    async def _sort_links(links):
        """
        sort links by their score then by the order they are defined in an adversary profile
        """
        return sorted(links, key=lambda k: (-k.score))

    async def _trim_links(self, operation, links, agent, ability_requirements=None):
        host_already_ran = [l.command for l in operation.chain if l.paw == agent.paw]
        links[:] = await self._add_test_variants(links, agent, operation, ability_requirements)
        links[:] = [l for l in links if l.command not in host_already_ran]
        links[:] = [l for l in links if
                    not re.findall(r'#{(.*?)}', b64decode(l.command).decode('utf-8'), flags=re.DOTALL)]
        self.log.debug('Created %d links for %s' % (len(links), agent.paw))
        return links

    async def _add_test_variants(self, links, agent, operation, ability_requirements=None):
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

    async def _do_enforcements(self, ability_requirements, operation, link, combo):
        for req_inst in ability_requirements:
            uf = link.get('used', [])
            requirements_info = dict(module=req_inst.module, enforcements=req_inst.relationships[0])
            requirement = await self.load_module('Requirement', requirements_info)
            if not requirement.enforce(combo[0], uf, operation['facts']):
                return False
        return True

    @staticmethod
    async def _build_relevant_facts(variables, operation, agent_facts):
        """
        Create a list of ([fact, value, score]) tuples for each variable/fact
        """
        facts = operation.all_facts()

        relevant_facts = []
        for v in variables:
            variable_facts = []
            for fact in [f for f in facts if f.prop == v]:
                if fact.prop.startswith('host'):
                    if fact.unique in agent_facts:
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
            score += (score + var.score)
            used.append(var)
            copy_test = copy_test.replace('#{%s}' % var.prop, var.value)
        return copy_test, score, used

    @staticmethod
    async def _get_agent_facts(operation, paw):
        agent_facts = []
        for link in [l for l in operation.chain if l.paw == paw]:
            for f in link.facts:
                agent_facts.append(f.unique)
        return agent_facts

    async def _default_link_status(self, operation):
        return self.LinkState.EXECUTE.value if operation.autonomous else self.LinkState.PAUSE.value
