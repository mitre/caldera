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
        """
        For an operation, phase and agent combination, determine which potential links can be executed
        :param operation:
        :param agent:
        :param phase:
        :return: a list of links
        """
        if (not agent['trusted']) and (not operation['allow_untrusted']):
            self.log.debug('Agent %s untrusted: no link created' % agent['paw'])
            return []
        phase_abilities = [i for p, v in operation['adversary']['phases'].items() if p <= phase for i in v]
        links = []
        capable_agent_abs = await self.capable_agent_abilities(phase_abilities, agent)
        for a in capable_agent_abs:
            links.append(
                dict(op_id=operation['id'], paw=agent['paw'], ability=a['id'], command=a['test'], score=0,
                     decide=datetime.now(), executor=a['executor'], jitter=self.jitter(operation['jitter'])))
        links[:] = await self._trim_links(operation, links, agent)
        await self._skipped_abilities(phase_abilities, capable_agent_abs, links, 
                                        agent, operation, phase)
        return [link for link in list(reversed(sorted(links, key=lambda k: k['score'])))]

    async def create_cleanup_links(self, operation):
        """
        For a given operation, create a link for every cleanup action on every executed ability
        :param operation:
        :return: None
        """
        op = await self.get_service('data_svc').explode_operation(criteria=dict(id=operation['id']))
        for member in op[0]['host_group']:
            if (not member['trusted']) and (not op[0]['allow_untrusted']):
                self.log.debug('Agent %s untrusted: no cleanup-link created' % member['paw'])
                continue
            links = []
            for link in await self.get_service('data_svc').explode_chain(criteria=dict(paw=member['paw'],
                                                                                       op_id=op[0]['id'])):
                ability = (await self.get_service('data_svc').explode_abilities(criteria=dict(id=link['ability'])))[0]
                if ability['cleanup']:
                    links.append(dict(op_id=op[0]['id'], paw=member['paw'], ability=ability['id'], cleanup=1,
                                      command=ability['cleanup'], executor=ability['executor'], score=0,
                                      decide=datetime.now(), jitter=0))
            links[:] = await self._trim_links(op[0], links, member)
            for link in reversed(links):
                link.pop('rewards', [])
                await self.get_service('data_svc').create('core_chain', link)
        await self.wait_for_phase(op[0])

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
            while next((True for lnk in op[0]['chain'] if lnk['paw'] == member['paw'] and not lnk['finish']),
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

    @staticmethod
    async def capable_agent_abilities(phase_abilities, agent):
        abilities = []
        preferred = next((e['executor'] for e in agent['executors'] if e['preferred']))
        for ai in set([pa['ability_id'] for pa in phase_abilities]):
            total_ability = [ab for ab in phase_abilities if ab['ability_id'] == ai]
            if len(total_ability) > 1:
                val = next((ta for ta in total_ability if ta['executor'] == preferred), False)
                if val:
                    abilities.append(val)
            elif total_ability[0]['executor'] in [e['executor'] for e in agent['executors']]:
                abilities.append(total_ability[0])
        return abilities

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

    async def _trust_issues(self, operation, paw):
        if not operation['allow_untrusted']:
            agent = await self.get_service('data_svc').explode_agents(criteria=dict(paw=paw))
            return not agent[0]['trusted']
        return False

    async def _skipped_abilities(self, phase_abilities, capable_agent_abs, links,
                                    agent, operation, phase):
        '''
        Save skipped abilities by the agent
        '''
        data_svc = self.get_service('data_svc')
        already_skipped = await data_svc.get('core_skipped_abilities', 
                                    dict(paw=agent['paw'], op_id=operation['id']))
        already_skipped_id = set([a['ability_id'] for a in already_skipped])
        already_ran = set([l['ability'] for l in operation['chain'] if l['paw'] == agent['paw']])
        already_ran_id = set([p['ability_id'] for p in phase_abilities if p['id'] in already_ran])
        already_checked = already_skipped_id.union(already_ran_id)
        phase_abilities_tuples = set([(p['id'],p['ability_id']) for p in phase_abilities 
                                    if p['ability_id'] not in already_checked])
        phase_abilities_id = set([ab_id for (i, ab_id) in phase_abilities_tuples])
        capable_abs_tuples = set([(c['id'],c['ability_id']) for c in capable_agent_abs 
                                    if c['ability_id'] not in already_checked])
        capable_abs_id = set([ab_id for (i, ab_id) in capable_abs_tuples])
        links_abs = set([l['ability'] for l in links])
        links_abs_tuples = set([(i, ab_id) for (i, ab_id) in capable_abs_tuples if i in links_abs])
        links_abs_id = set([ab_id for (i, ab_id) in links_abs_tuples])
        for ab_id in (phase_abilities_id - capable_abs_id):
            await data_svc.create('core_skipped_abilities', dict(ability_id=ab_id, paw=agent['paw'], 
                    op_id=operation['id'], phase=phase, reason='incompatible executors'))
        for ab_id in (capable_abs_id - links_abs_id):
            await data_svc.create('core_skipped_abilities', dict(ability_id=ab_id, paw=agent['paw'], 
                    op_id=operation['id'], phase=phase, reason='variables not replaced'))
            
