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
        :param agent:
        :return: trimmed list of links
        """
        links[:] = await self.add_test_variants(operation, agent, links, ability_requirements)
        links = await self.remove_completed_links(operation, links, agent)
        links = await self.remove_links_missing_facts(links)
        self.log.debug('Created %d links for %s' % (len(links), agent['paw']))
        return links

    async def add_test_variants(self, operation, agent, links, ability_requirements=None):
        """
        Create a list of all possible links for a given phase
        :param operation:
        :param agent:
        :param links:
        :param ability_requirements:
        return: list of links, with additional variant links
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