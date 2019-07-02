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
        self.log.debug('Created %d links for %s' % (len(links), agent['paw']))
        return [link for link in list(reversed(sorted(links, key=lambda k: k['score'])))]

    async def wait_for_phase(self, op_id, agent_id):
        op = await self.data_svc.explode_operation(dict(id=op_id))
        while next((lnk for lnk in op[0]['chain'] if lnk['host_id'] == agent_id and not lnk['finish']), False):
            await asyncio.sleep(2)
            op = await self.data_svc.explode_operation(dict(id=op_id))

    """ PRIVATE """

    async def _add_test_variants(self, links, agent, operation):
        """
        Create a list of all possible links for a given phase
        """
        group = operation['host_group']['name']
        for link in links:
            decoded_test = b64decode(link['command']).decode('utf-8')
            decoded_test = decoded_test.replace('#{server}', agent['server'])
            decoded_test = decoded_test.replace('#{group}', group)
            decoded_test = decoded_test.replace('#{files}', agent['files'])

            variables = re.findall(r'#{(.*?)}', decoded_test, flags=re.DOTALL)
            if variables:
                relevant_facts = await self._build_relevant_facts(variables, operation.get('facts', []))
                for combo in list(itertools.product(*relevant_facts)):
                    copy_test = copy.deepcopy(decoded_test)
                    copy_link = copy.deepcopy(link)

                    cleanup_cmd = self.utility_svc.decode_bytes(copy_link.get('cleanup'))
                    variant, cleanup, score, rewards = await self._build_single_test_variant(copy_test, cleanup_cmd, combo)
                    copy_link['command'] = await self._apply_stealth(operation, agent, variant)
                    copy_link['cleanup'] = self.utility_svc.encode_string(cleanup)
                    copy_link['score'] = score
                    copy_link['rewards'] = rewards
                    links.append(copy_link)
            else:
                link['command'] = await self._apply_stealth(operation, agent, decoded_test)
        return links

    @staticmethod
    async def _build_relevant_facts(variables, facts):
        """
        Create a list of ([fact, value, score]) tuples for each variable/fact
        """
        facts = [f for f in facts if not f['blacklist']]
        relevant_facts = []
        for v in variables:
            variable_facts = []
            for fact in facts:
                if fact['property'] == v:
                    variable_facts.append((fact['property'], fact['value'], fact['score'], fact['id']))
            relevant_facts.append(variable_facts)
        return relevant_facts

    @staticmethod
    async def _build_single_test_variant(copy_test, clean_test, combo):
        """
        Replace all variables with facts from the combo to build a single test variant
        """
        score, rewards = 0, []
        for var in combo:
            score += (score + var[2])
            rewards.append(var[3])
            copy_test = copy_test.replace('#{%s}' % var[0], var[1])
            clean_test = clean_test.replace('#{%s}' % var[0], var[1])
        return copy_test, clean_test, score, rewards

    async def _apply_stealth(self, operation, agent, decoded_test):
        if operation['stealth']:
            decoded_test = self.utility_svc.apply_stealth(agent['platform'], decoded_test)
        return self.utility_svc.encode_string(decoded_test)
