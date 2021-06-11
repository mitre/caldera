import copy
import itertools
import logging
import re
from base64 import b64decode

from app.utility.base_service import BaseService
from app.utility.rule_set import RuleSet


class BasePlanningService(BaseService):
    # Matches facts/variables.
    # Group 1 returns the trait, including any limits
    # Ex: '#{server.malicious.url}' => 'server.malicious.url'
    # Ex: '#{host.file.path[filters(technique=T1005,max=3)]}' => 'host.file.path[filters(technique=T1005,max=3)]'
    re_variable = re.compile(r'#{(.*?)}', flags=re.DOTALL)

    # Matches facts/variables that contain limits, denoted by brackets in the fact name.
    # Ex: Matches '#{host.file.path[filters(technique=T1005,max=3)]}'
    # Ex: Does not match: '#{server.malicious.url}'
    re_limited = re.compile(r'#{.*\[*\]}')

    # Matches the trait of a limited fact
    # Group 0 returns the trait excluding any limits
    # Ex: Does not match non-limited fact '#{server.malicious.url}'
    # Ex: #{host.file.path[filters(technique=T1005,max=3)]} => 'host.file.path'
    re_trait = re.compile(r'(?<=\{).+?(?=\[)')

    # Matches trait limits.
    # Group 0 returns the specific filters.
    # Ex: '#{host.file.path[filters(technique=T1005,max=3)]}' => 'technique=T1005,max=3'
    re_index = re.compile(r'(?<=\[filters\().+?(?=\)\])')

    def __init__(self, global_variable_owners=None):
        """Base class for Planning Service

        Args:
            global_variable_owners: List of objects/classes that expose an is_global_variable() method that accepts
                an 'unwrapped' variable string (e.g. 'foo.bar.baz' and NOT '#{foo.bar.baz}') and returns True if
                it is a global variable.
        """
        self._global_variable_owners = list(global_variable_owners or ())

    def add_global_variable_owner(self, global_variable_owner):
        """Adds a global variable owner to the internal registry.

        These will be used for identification of global variables when performing variable-fact substitution.

        Args:
            global_variable_owner: An object that exposes an is_global_variable(...) method and accepts a string
                containing a bare/unwrapped variable.
        """
        self._global_variable_owners.append(global_variable_owner)

    def is_global_variable(self, variable):
        return any(x.is_global_variable(variable) for x in self._global_variable_owners)

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
        links[:] = await self.add_test_variants(links, agent, await operation.all_facts(), operation.rules)
        links = await self.remove_links_with_unset_variables(links)
        links = await self.remove_links_missing_requirements(links, operation)
        links = await self.obfuscate_commands(agent, operation.obfuscator, links)
        links = await self.remove_completed_links(operation, agent, links)
        return links

    async def add_test_variants(self, links, agent, facts=(), rules=()):
        """
        Create a list of all possible links for a given set of templates

        :param links:
        :param agent:
        :param facts:
        :param rules:
        :return: updated list of links
        """
        link_variants = []

        for link in links:
            decoded_test = agent.replace(link.command, file_svc=self.get_service('file_svc'))
            variables = set(x for x in re.findall(self.re_variable, decoded_test) if not self.is_global_variable(x))

            if variables:
                relevant_facts = await self._build_relevant_facts(variables, facts)

                if relevant_facts:
                    good_facts = [await RuleSet(rules=rules).apply_rules(facts=fact_set) for fact_set in relevant_facts]
                    valid_facts = [await self._trim_by_limit(decoded_test, g_fact[0]) for g_fact in good_facts]

                    if not valid_facts:
                        continue

                    for combo in list(itertools.product(*valid_facts)):
                        try:
                            copy_test = copy.copy(decoded_test)
                            copy_link = copy.deepcopy(link)
                            variant, score, used = await self._build_single_test_variant(copy_test, combo,
                                                                                         link.executor.name)
                            copy_link.command = self.encode_string(variant)
                            copy_link.score = score
                            copy_link.used.extend(used)
                            copy_link.apply_id(agent.host)
                            link_variants.append(copy_link)
                        except Exception as ex:
                            logging.error('Could not create test variant: %s.\nLink=%s' % (ex, link.__dict__))
            else:
                # apply_id() modifies link.command so the order of these operations matter
                link.command = self.encode_string(decoded_test)
                link.apply_id(agent.host)

        return links + link_variants

    @staticmethod
    async def remove_completed_links(operation, agent, links):
        """
        Remove any links that have already been completed by the operation for the agent

        :param operation:
        :param links:
        :param agent:
        :return: updated list of links
        """
        completed_links = [lnk for lnk in operation.chain if lnk.paw == agent.paw and (lnk.finish or lnk.can_ignore())]

        singleton_links = BasePlanningService._list_historic_duplicate_singletons(operation)

        return [lnk for lnk in links if lnk.ability.repeatable or
                (lnk not in completed_links and
                 not any([lnk.command == x.command for x in singleton_links]))]

    @staticmethod
    async def remove_links_with_unset_variables(links):
        """
        Remove any links that contain variables that have not been filled in.

        :param links:
        :return: updated list of links
        """
        links[:] = [s_link for s_link in links if not
                    BasePlanningService.re_variable.findall(b64decode(s_link.command).decode('utf-8'))]
        return links

    async def remove_links_missing_requirements(self, links, operation):
        links[:] = [s_link for s_link in links if s_link.cleanup or await self._do_enforcements(s_link, operation)]
        return links

    @staticmethod
    async def remove_links_above_visibility(links, operation):
        links[:] = [s_link for s_link in links if operation.visibility >= s_link.visibility.score]
        return links

    async def obfuscate_commands(self, agent, obfuscator, links):
        o = (await self.get_service('data_svc').locate('obfuscators', match=dict(name=obfuscator)))[0]
        mod = o.load(agent)
        for s_link in links:
            s_link.command = self.encode_string(mod.run(s_link))
        return links

    """ PRIVATE """

    @staticmethod
    def _list_historic_duplicate_singletons(operation):
        """
        Generate a list of successfully run singleton abilities for a given operation
        :param operation: Operation to scan
        :return: List of command hashes for succeeded singleton abilities
        """
        singleton = [k for k in operation.chain if k.status == k.states['SUCCESS'] and k.ability.singleton]
        return [x for x in singleton if x]

    @staticmethod
    def _remove_links_of_duplicate_singletons(agent_links):
        """
        Filter links across agents
        :param agent_links: array of agent links
        :return: Flattened, filtered list of links
        """

        links = []
        parallel_list = []
        for agent_list in agent_links:
            for individual_link in agent_list:
                if not individual_link.ability.singleton:
                    links.append(individual_link)
                else:
                    compare = (individual_link.command_hash if individual_link.command_hash else
                               individual_link.command)
                    if compare not in parallel_list:
                        parallel_list.append(compare)
                        links.append(individual_link)
        return links

    @staticmethod
    async def _build_single_test_variant(copy_test, combo, executor):
        """
        Replace all variables with facts from the combo to build a single test variant
        """
        score, used = 0, list()
        for var in combo:
            score += (score + var.score)
            used.append(var)

            # Matches a complete fact with a given trait
            # Ex: Matches ${a}
            # Ex: Matches ${a.b.c}
            # Ex: Matches ${a.b.c[filters(max=3)]}
            pattern = r'#{(%s(?=[\[}]).*?)}' % re.escape(var.trait)
            re_variable = re.compile(pattern, flags=re.DOTALL)
            copy_test = re.sub(re_variable, str(var.escaped(executor)).strip().encode('unicode-escape').decode('utf-8'),
                               copy_test)
        return copy_test, score, used

    @staticmethod
    def _is_fact_bound(fact):
        return not fact['link_id']

    @staticmethod
    async def _build_relevant_facts(variables, facts):
        """
        Create a list of facts which are relevant to the given ability's defined variables

        Returns: (list) of lists, with each inner list providing all known values for the corresponding fact trait
        """
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
                requirements_info = dict(module=req_inst.module, enforcements=req_inst.relationship_match[0])
                requirement = await self.load_module('Requirement', requirements_info)
                if not await requirement.enforce(link, operation):
                    return False
        return True

    async def _trim_by_limit(self, decoded_test, facts):
        limited_facts = []
        for limit in re.findall(self.re_limited, decoded_test):
            limited = copy.deepcopy(facts)
            trait = re.search(self.re_trait, limit).group(0).split('#{')[-1]

            limit_definitions = re.search(self.re_index, limit).group(0)
            if limit_definitions:
                for limiter in limit_definitions.split(','):
                    limited = self._apply_limiter(trait=trait, limiter=limiter.split('='), facts=limited)
            if limited:
                limited_facts.extend(limited)
        if limited_facts:
            return limited_facts
        return facts

    @staticmethod
    def _apply_limiter(trait, limiter, facts):
        if limiter[0] == 'max':
            return sorted([f for f in facts if f.trait == trait], key=lambda k: (-k.score))[:int(limiter[1])]
        if limiter[0] == 'technique':
            return [f for f in facts if f.technique_id == limiter[1]]
