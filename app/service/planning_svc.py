import asyncio
import copy
import itertools
import re
from base64 import b64decode
from datetime import datetime

from app.service.base_service import BaseService


class PlanningService(BaseService):

    def __init__(self):
        self.log = self.add_service('planning_svc', self)

    async def select_links(self, operation, agent, phase):
        phase_abilities = [i for p, v in operation['adversary']['phases'].items() if p <= phase for i in v]
        phase_abilities[:] = [p for p in phase_abilities if
                              agent['platform'] == p['platform'] and p['executor'] in agent['executors']]
        final_phase_abilities = await self._trim_multiple_agent_abilities(phase_abilities, agent)
        links = []
        for a in final_phase_abilities:
            links.append(
                dict(op_id=operation['id'], paw=agent['paw'], ability=a['id'], command=a['test'], score=0,
                     decide=datetime.now(), jitter=self.jitter(operation['jitter'])))
        links[:] = await self._trim_links(operation, links, agent)
        return [link for link in list(reversed(sorted(links, key=lambda k: k['score'])))]

    async def create_cleanup_links(self, operation):
        for member in operation['host_group']:
            links = []
            for link in await self.get_service('data_svc').explode_chain(criteria=dict(paw=member['paw'],
                                                                     op_id=operation['id'])):
                ability = (await self.get_service('data_svc').explode_abilities(criteria=dict(id=link['ability'])))[0]
                if ability['cleanup']:
                    links.append(dict(op_id=operation['id'], paw=member['paw'], ability=ability['id'], cleanup=1,
                                      command=ability['cleanup'], score=0, decide=datetime.now(), jitter=0))
            links[:] = await self._trim_links(operation, links, member)
            for link in reversed(links):
                link.pop('rewards', [])
                await self.get_service('data_svc').create_link(link)

    async def wait_for_phase(self, operation):
        for member in operation['host_group']:
            op = await self.get_service('data_svc').explode_operation(dict(id=operation['id']))
            while next((True for lnk in op[0]['chain'] if lnk['paw'] == member['paw'] and not lnk['finish']),
                       False):
                await asyncio.sleep(3)
                op = await self.get_service('data_svc').explode_operation(dict(id=operation['id']))

    async def decode(self, encoded_cmd, agent, group):
        decoded_cmd = self.decode_bytes(encoded_cmd)
        decoded_cmd = decoded_cmd.replace('#{server}', agent['server'])
        decoded_cmd = decoded_cmd.replace('#{group}', group)
        decoded_cmd = decoded_cmd.replace('#{paw}', agent['paw'])
        decoded_cmd = decoded_cmd.replace('#{location}', agent['location'])
        return decoded_cmd

    """ PRIVATE """

    async def _trim_links(self, operation, links, agent):
        host_already_ran = [l['command'] for l in operation['chain'] if l['paw'] == agent['paw'] and l['collect']]
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
                for combo in list(itertools.product(*relevant_facts)):
                    copy_test = copy.deepcopy(decoded_test)
                    copy_link = copy.deepcopy(link)

                    variant, score, rewards = await self._build_single_test_variant(copy_test, combo)
                    copy_link['command'] = await self._apply_stealth(operation, agent, variant)
                    copy_link['score'] = score
                    copy_link['rewards'] = rewards
                    links.append(copy_link)
            else:
                link['command'] = await self._apply_stealth(operation, agent, decoded_test)
        return links

    """ PRIVATE """

    @staticmethod
    def _reward_fact_relationship(combo_set, combo_link, score):
        if len(combo_set) == 1 and len(combo_link) == 1:
            score *= 2
        return score

    @staticmethod
    async def _build_relevant_facts(variables, facts, agent_facts):
        """
        Create a list of ([fact, value, score]) tuples for each variable/fact
        """
        facts = [f for f in facts if f['score'] > 0]
        relevant_facts = []
        for v in variables:
            variable_facts = []
            for fact in [f for f in facts if f['property'] == v]:
                if fact['property'].startswith('host'):
                    if fact['id'] in agent_facts:
                        variable_facts.append(fact)
                else:
                    variable_facts.append(fact)
            relevant_facts.append(variable_facts)
        return relevant_facts

    async def _build_single_test_variant(self, copy_test, combo):
        """
        Replace all variables with facts from the combo to build a single test variant
        """
        score, rewards, combo_set_id, combo_link_id = 0, list(), set(), set()
        for var in combo:
            score += (score + var['score'])
            rewards.append(var['id'])
            copy_test = copy_test.replace('#{%s}' % var['property'], var['value'])
            combo_set_id.add(var['set_id'])
            combo_link_id.add(var['link_id'])
        score = self._reward_fact_relationship(combo_set_id, combo_link_id, score)
        return copy_test, score, rewards

    async def _apply_stealth(self, operation, agent, decoded_test):
        if operation['stealth']:
            decoded_test = self.apply_stealth(agent['platform'], decoded_test)
        return self.encode_string(decoded_test)

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

    async def _trim_multiple_agent_abilities(self, phase_abilities, agent):
        """
        Trim the phase abilities for this specific agent to only include a single ability variant if multiple executors
        exist for that ability.  By default, the agent will select use the first entry in core_executors as its primary
        executor.
        :param phase_abilities: available abilities for current operation phase
        :param agent: the current agent that is being tasked
        :return: list of trimmed phase abilities where the ability use the agent's primary executor (if multiple options)
        """
        final_phase_abilities = []
        exists = set()
        for p in phase_abilities:
            if p['ability_id'] not in exists:
                ability = await self.get_service('data_svc').get('core_ability',
                                                                 criteria=dict(ability_id=p['ability_id']))
                if len(ability) > 1:
                    for ab in ability:
                        if ab['executor'] == agent['executors'][0]:
                            ability = ab
                            break
                else:
                    ability = ability[0]
                exists.add(p['ability_id'])
                final_phase_abilities.append(ability)
        return final_phase_abilities
