import glob
from base64 import b64encode
from collections import defaultdict
from datetime import datetime
from uuid import UUID, uuid4
import logging
import yaml

logger = logging.getLogger('DataService')
logger.setLevel('INFO')


class DataService:

    def __init__(self, dao):
        self.dao = dao

    async def reload_database(self, schema='conf/core.sql', adversaries=None, abilities=None):
        with open(schema) as schema:
            await self.dao.build(schema.read())
        await self.load_abilities(directory=abilities)
        await self.load_adversaries(config=adversaries)

    async def load_adversaries(self, config):
        if config:
            with open(config) as seed:
                for doc in yaml.load_all(seed):
                    for adv in doc[0]['adversaries']:
                        phases = [dict(phase=k, id=i) for k, v in adv['phases'].items() for i in v]
                        await self.create_adversary(adv['name'], adv['description'], phases)

    async def load_abilities(self, directory):
        for filename in glob.iglob('%s/**/*.yml' % directory, recursive=True):
            f = make_uuid(filename)
            with open(f) as ability:
                for ab in yaml.load(ability):
                    for ex,el in ab['executors'].items():
                        encoded_test = b64encode(el['command'].strip().encode('utf-8'))
                        await self.create_ability(id=ab.get('id'), tactic=ab['tactic'], technique=ab['technique'], name=ab['name'],
                                                  test=encoded_test.decode(), description=ab.get('description'), executor=ex,
                                                  cleanup=b64encode(el['cleanup'].strip().encode('utf-8')).decode() if el.get('cleanup') else None,
                                                  parser=el.get('parser'))

    """ CREATE """

    async def create_ability(self, id, tactic, technique, name, test, description, executor, cleanup=None, parser=None):
        await self.dao.delete('core_ability', dict(id=id, executor=executor))
        await self.dao.create('core_attack', dict(attack_id=technique['attack_id'], name=technique['name'], tactic=tactic))
        entry = await self.dao.get('core_attack', dict(attack_id=technique['attack_id']))
        entry_id = entry[0]['attack_id']
        await self.dao.create('core_ability', dict(id=id, name=name, test=test, technique=entry_id, executor=executor, description=description, cleanup=cleanup))
        if parser:
            parser['ability_id'] = id
            await self.dao.create('core_parser', parser)
        return 'Saved ability: %s' % id

    async def create_adversary(self, name, description, phases):
        identifier = await self.dao.create('core_adversary', dict(name=name.lower(), description=description))
        await self.dao.delete('core_adversary_map', dict(adversary_id=identifier))
        for ability in phases:
            a = (dict(adversary_id=identifier, phase=ability['phase'], ability_id=ability['id']))
            await self.dao.create('core_adversary_map', a)
        return 'Saved adversary: %s' % name

    async def create_group(self, name, paws):
        identifier = await self.dao.create('core_group', dict(name=name))
        for paw in paws:
            agent = await self.dao.get('core_agent', dict(paw=paw))
            await self.dao.create('core_group_map', dict(group_id=identifier, agent_id=agent[0]['id']))
        return 'Saved %s host group' % name

    async def create_operation(self, name, group, adversary, jitter='3/5', cleanup=True, stealth=False):
        return await self.dao.create('core_operation', dict(
            name=name, host_group=group, adversary=adversary, finish=None, phase=0, jitter=jitter,
            start=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cleanup=cleanup, stealth=stealth)
        )

    async def create_link(self, link, cleanup=None):
        link_id = await self.dao.create('core_chain', link)
        if cleanup and cleanup.get('command'):
            cleanup['link_id'] = link_id
            await self.dao.create('core_cleanup', cleanup)
        return link_id

    """ VIEW """

    async def explode_abilities(self, criteria=None):
        abilities = await self.dao.get('core_ability', criteria=criteria)
        for ab in abilities:
            ab['cleanup'] = '' if ab['cleanup'] is None else ab['cleanup']
            ab['parser'] = await self.dao.get('core_parser', dict(ability_id=ab['id']))
            ab['technique'] = (await self.dao.get('core_attack', dict(attack_id=ab['technique'])))[0]
        return abilities

    async def explode_adversaries(self, criteria=None):
        adversaries = await self.dao.get('core_adversary', criteria)
        for adv in adversaries:
            phases = defaultdict(list)
            for t in await self.dao.get('core_adversary_map', dict(adversary_id=adv['id'])):
                for ability in await self.explode_abilities(dict(id=t['ability_id'])):
                    phases[t['phase']].append(ability)
            adv['phases'] = dict(phases)
        return adversaries

    async def explode_operation(self, criteria=None):
        operations = await self.dao.get('core_operation', criteria)
        for op in operations:
            op['chain'] = sorted(await self.explode_chain(op['id']), key=lambda k: k['id'])
            groups = await self.explode_groups(dict(id=op['host_group']))
            op['host_group'] = groups[0]
            adversaries = await self.explode_adversaries(dict(id=op['adversary']))
            op['adversary'] = adversaries[0]
        return operations

    async def explode_groups(self, criteria=None):
        groups = await self.dao.get('core_group', criteria=criteria)
        for g in groups:
            g['agents'] = await self.dao.get('core_group_map', dict(group_id=g['id']))
        return groups

    async def explode_agents(self, criteria: object = None) -> object:
        agents = await self.dao.get('core_agent', criteria)
        sql = 'SELECT g.id, g.name, m.agent_id FROM core_group g JOIN core_group_map m on g.id=m.group_id'
        groups = await self.dao.raw_select(sql)
        for a in agents:
            a['groups'] = [dict(id=g['id'], name=g['name']) for g in groups if g['agent_id'] == a['id']]
        return agents

    async def explode_results(self, criteria=None):
        return await self.dao.get('core_result', criteria=criteria)

    async def explode_chain(self, op_id):
        sql = 'SELECT a.*, b.name as abilityName, b.description as abilityDescription ' \
              'FROM core_chain a '\
              'JOIN (SELECT id, name, description FROM core_ability GROUP BY id) b ' \
              'ON a.ability_id=b.id ' \
              'WHERE a.op_id = %s;' % op_id
        return await self.dao.raw_select(sql)

def make_uuid(_filename):
    uuid_string = _filename.split('/')[-1].split('.')[0]
    try:
        val = UUID(uuid_string, version=4)
        return _filename
    except ValueError:
        _uuid = str(uuid4())
        new_ability_file = _filename.split('/')[:-1]
        new_ability_file.append('{}.yml'.format(_uuid))
        new_ability_file = '/'.join(new_ability_file)
        with open(_filename, 'r') as ability:
            with open(new_ability_file, 'w') as new_ability:
                for line in ability:
                    if '- id:' in line:
                        l = '- id: {}\n'.format(_uuid)
                        new_ability.write(l)
                    else:
                        new_ability.write(line)
        logger.warning("Created new ability file with uuid: {}".format( new_ability_file))
        return new_ability_file
