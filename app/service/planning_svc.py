import asyncio
import re
import copy
import itertools

from datetime import datetime
from base64 import b64decode


class PlanningService:

    def __init__(self, data_svc, utility_svc):
        self.data_svc = data_svc
        self.utility_svc = utility_svc
        self.log = utility_svc.create_logger('planning_svc')

    async def select_links(self, operation, agent, phase):
        host_already_ran = [l['command'] for l in operation['chain'] if l['host_id'] == agent['id'] and l['collect']]
        phase_abilities = [i for p, v in operation['adversary']['phases'].items() if p <= phase for i in v]
        phase_abilities[:] = [p for p in phase_abilities if agent['platform'] == p['platform']]
        links = []
        for a in phase_abilities:
            links.append(
                dict(op_id=operation['id'], host_id=agent['id'], ability=a['id'], command=a['test'], score=0,
                     decide=datetime.now(), jitter=self.utility_svc.jitter(operation['jitter']), cleanup=a.get('cleanup')))
        links[:] = await self._add_test_variants(links, agent, operation)
        links[:] = [l for l in links if l['command'] not in host_already_ran]
        links[:] = [l for l in links if
                    not re.findall(r'#{(.*?)}', b64decode(l['command']).decode('utf-8'), flags=re.DOTALL)]
        await self._remove_cleanup_cmds(operation, links)
        self.log.debug('Created %d links for %s' % (len(links), agent['paw']))
        return [link for link in list(reversed(sorted(links, key=lambda k: k['score'])))]

    async def wait_for_phase(self, operation):
        for member in operation['host_group']:
            op = await self.data_svc.explode_operation(dict(id=operation['id']))
            while next((True for lnk in op[0]['chain'] if lnk['host_id'] == member['id'] and not lnk['finish']),
                       False):
                await asyncio.sleep(3)
                op = await self.data_svc.explode_operation(dict(id=operation['id']))

    async def decode(self, encoded_cmd, agent, group):
        decoded_cmd = self.utility_svc.decode_bytes(encoded_cmd)
        decoded_cmd = decoded_cmd.replace('#{server}', agent['server'])
        decoded_cmd = decoded_cmd.replace('#{group}', group)
        decoded_cmd = decoded_cmd.replace('#{files}', agent['files'])
        return decoded_cmd

    """ PRIVATE """

    async def _add_test_variants(self, links, agent, operation):
        """
        Create a list of all possible links for a given phase
        """
        group = agent['host_group']
        for link in links:
            decoded_test = await self.decode(link['command'], agent, group)
            cleanup_cmd = await self.decode(link.get('cleanup'), agent, group)

            variables = re.findall(r'#{(.*?)}', decoded_test, flags=re.DOTALL)
            if variables:
                relevant_facts = await self._build_relevant_facts(variables, operation.get('facts', []))
                for combo in list(itertools.product(*relevant_facts)):
                    copy_test = copy.deepcopy(decoded_test)
                    copy_link = copy.deepcopy(link)

                    variant, cleanup, score, rewards = await self._build_single_test_variant(copy_test, cleanup_cmd, combo)
                    copy_link['command'] = await self._apply_stealth(operation, agent, variant)
                    copy_link['cleanup'] = self.utility_svc.encode_string(cleanup)
                    copy_link['score'] = score
                    copy_link['rewards'] = rewards
                    links.append(copy_link)
            else:
                link['command'] = await self._apply_stealth(operation, agent, decoded_test)
                link['cleanup'] = await self._apply_stealth(operation, agent, cleanup_cmd)
        return links

    """ PRIVATE """

    @staticmethod
    def _reward_fact_relationship(combo_set, combo_link, score):
        if len(combo_set) == 1 and len(combo_link) == 1:
            score *= 2
        return score

    @staticmethod
    async def _build_relevant_facts(variables, facts):
        """
        Create a list of ([fact, value, score]) tuples for each variable/fact
        """
        facts = [f for f in facts if f['score'] > 0]
        relevant_facts = []
        for v in variables:
            variable_facts = []
            for fact in facts:
                if fact['property'] == v:
                    variable_facts.append(fact)
            relevant_facts.append(variable_facts)
        return relevant_facts

    async def _build_single_test_variant(self, copy_test, clean_test, combo):
        """
        Replace all variables with facts from the combo to build a single test variant
        """
        score, rewards, combo_set_id, combo_link_id = 0, list(), set(), set()
        for var in combo:
            score += (score + var['score'])
            rewards.append(var['id'])
            copy_test = copy_test.replace('#{%s}' % var['property'], var['value'])
            clean_test = clean_test.replace('#{%s}' % var['property'], var['value'])
            combo_set_id.add(var['set_id'])
            combo_link_id.add(var['link_id'])
        score = self._reward_fact_relationship(combo_set_id, combo_link_id, score)
        return copy_test, clean_test, score, rewards

    async def _apply_stealth(self, operation, agent, decoded_test):
        if operation['stealth']:
            decoded_test = self.utility_svc.apply_stealth(agent['platform'], decoded_test)
        return self.utility_svc.encode_string(decoded_test)

    @staticmethod
    async def _remove_cleanup_cmds(operation, links):
        if not operation['cleanup']:
            for link in links:
                link['cleanup'] = None
