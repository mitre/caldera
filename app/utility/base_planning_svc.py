import copy
import itertools
import logging
import re
from base64 import b64decode

from app.utility.base_service import BaseService
from app.utility.rule_set import RuleSet


class BasePlanningService(BaseService):

    re_variable = re.compile(r'#{(.*?)}', flags=re.DOTALL)
    re_limited = re.compile(r'#{.*\[*\]}')
    re_trait = re.compile(r'(?<=\{).+?(?=\[)')
    re_index = re.compile(r'(?<=\[filters\().+?(?=\)\])')

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
        links = await self.remove_links_missing_facts(links)
        links = await self.remove_links_missing_requirements(links, operation)
        links = await self.obfuscate_commands(agent, operation.obfuscator, links)
        links = await self.remove_completed_links(operation, agent, links)
        return links

    async def add_test_variants(self, links, agent, operation):
        """
        Create a list of all possible links for a given phase

        :param links:
        :param agent:
        :param operation:
        :return: updated list of links
        """
        for link in links:
            decoded_test = agent.replace(link.command)
            variables = re.findall(self.re_variable, decoded_test)
            if variables:
                relevant_facts = await self._build_relevant_facts(variables, operation)
                good_facts = await RuleSet(rules=operation.rules).apply_rules(facts=relevant_facts[0])
                valid_facts = await self._trim_by_limit(decoded_test, good_facts)
                for combo in list(itertools.product(*valid_facts)):
                    try:
                        copy_test = copy.copy(decoded_test)
                        copy_link = copy.deepcopy(link)
                        variant, score, used = await self._build_single_test_variant(copy_test, combo, link.ability.executor)
                        copy_link.command = self.encode_string(variant)
                        copy_link.score = score
                        copy_link.used.extend(used)
                        copy_link.apply_id(agent.host)
                        links.append(copy_link)
                    except Exception as ex:
                        logging.error('Could not create test variant: %s.\nLink=%s' % (ex, link.__dict__))
            else:
                link.apply_id(agent.host)
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
                           if l.paw == agent.paw and (l.finish or l.can_ignore())]
        return [l for l in links if l.ability.repeatable or l.command not in completed_links]

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
        links[:] = [l for l in links if l.cleanup or await self._do_enforcements(l, operation)]
        return links

    @staticmethod
    async def remove_links_above_visibility(links, operation):
        links[:] = [l for l in links if operation.visibility >= l.visibility.score]
        return links

    async def obfuscate_commands(self, agent, obfuscator, links):
        o = (await self.get_service('data_svc').locate('obfuscators', match=dict(name=obfuscator)))[0]
        mod = o.load(agent)
        for l in links:
            l.command = self.encode_string(mod.run(l))
        return links

    """ PRIVATE """

    @staticmethod
    async def _build_single_test_variant(copy_test, combo, executor):
        """
        Replace all variables with facts from the combo to build a single test variant
        """
        score, used = 0, list()
        for var in combo:
            score += (score + var.score)
            used.append(var)
            re_variable = re.compile(r'#{(%s.*?)}' % var.trait, flags=re.DOTALL)
            copy_test = re.sub(re_variable, str(var.escaped(executor)).strip().encode('unicode-escape').decode('utf-8'), copy_test)
        return copy_test, score, used

    @staticmethod
    def _is_fact_bound(fact):
        return not fact['link_id']

    @staticmethod
    async def _build_relevant_facts(variables, operation):
        """
        Create a list of facts which are relevant to the given ability's defined variables
        """
        facts = operation.all_facts()

        relevant_facts = []
        for v in variables:
            variable_facts = []
            for fact in [f for f in facts if f.trait == v.split('[')[0]]:
                variable_facts.append(fact)
            relevant_facts.append(variable_facts)
        return relevant_facts

    async def _do_enforcements(self, link, operation):
        """
        enforce any defined requirements on the link
        """
        for req_inst in link.ability.requirements:
            if req_inst.module not in operation.planner.ignore_enforcement_modules:
                requirements_info = dict(module=req_inst.module, enforcements=req_inst.relationships[0])
                requirement = await self.load_module('Requirement', requirements_info)
                if not await requirement.enforce(link, operation):
                    return False
        return True

    async def _trim_by_limit(self, decoded_test, facts):
        limited_facts = []
        for limit in re.findall(self.re_limited, decoded_test):
            limited = copy.deepcopy(facts[0])
            trait = re.search(self.re_trait, limit).group(0)

            limit_definitions = re.search(self.re_index, limit).group(0)
            if limit_definitions:
                for limiter in limit_definitions.split(','):
                    limited = self._apply_limiter(trait=trait, limiter=limiter.split('='), facts=limited)
            limited_facts.append(limited)
        if limited_facts:
            return limited_facts
        return facts

    @staticmethod
    def _apply_limiter(trait, limiter, facts):
        if limiter[0] == 'max':
            return sorted([f for f in facts if f.trait == trait], key=lambda k: (-k.score))[:int(limiter[1])]
        if limiter[0] == 'technique':
            return [f for f in facts if f.technique_id == limiter[1]]
