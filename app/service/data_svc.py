import glob
import json
from base64 import b64encode
from collections import defaultdict

import yaml

from app.service.base_service import BaseService


class DataService(BaseService):

    def __init__(self, dao):
        self.dao = dao
        self.log = self.add_service('data_svc', self)

    async def load_data(self, directory=None, schema='conf/core.sql'):
        """
        Read all the data sources to populate the SQL database
        :param directory:
        :param schema:
        :return: None
        """
        with open(schema) as schema:
            await self.dao.build(schema.read())
        if directory:
            self.log.debug('Loading data from %s' % directory)
            await self.load_abilities(directory='%s/abilities' % directory)
            await self.load_adversaries(directory='%s/adversaries' % directory)
            await self.load_facts(directory='%s/facts' % directory)
            await self.load_planner(directory='%s/planners' % directory)

    async def load_abilities(self, directory):
        """
        For a given directory, load all abilities into the database
        :param directory:
        :return: None
        """
        for filename in glob.iglob('%s/**/*.yml' % directory, recursive=True):
            for entries in self.strip_yml(filename):
                for ab in entries:
                    for pl, executors in ab['platforms'].items():
                        for name, info in executors.items():
                            for e in name.split(','):
                                encoded_test = b64encode(info['command'].strip().encode('utf-8'))
                                await self.create_ability(ability_id=ab.get('id'), tactic=ab['tactic'].lower(),
                                                          technique_name=ab['technique']['name'],
                                                          technique_id=ab['technique']['attack_id'],
                                                          test=encoded_test.decode(), description=ab.get('description'),
                                                          executor=e, name=ab['name'], platform=pl,
                                                          cleanup=b64encode(
                                                              info['cleanup'].strip().encode(
                                                                  'utf-8')).decode() if info.get(
                                                              'cleanup') else None,
                                                          payload=info.get('payload'), parser=info.get('parser'))

    async def load_adversaries(self, directory):
        """
        Load all adversary YML files into the database
        :param directory:
        :return: None
        """
        for filename in glob.iglob('%s/*.yml' % directory, recursive=True):
            for adv in self.strip_yml(filename):
                phases = [dict(phase=k, id=i) for k, v in adv['phases'].items() for i in v]
                await self.create_adversary(adv['id'], adv['name'], adv['description'], phases)

    async def load_facts(self, directory):
        """
        Load all fact YML files into the database
        :param directory:
        :return: None
        """
        for filename in glob.iglob('%s/*.yml' % directory, recursive=False):
            for source in self.strip_yml(filename):
                source_id = await self.dao.create('core_source', dict(name=source['name']))
                for fact in source['facts']:
                    fact['source_id'] = source_id
                    await self.create_fact(**fact)

    async def load_planner(self, directory):
        """
        Load all planner YML files into the database
        :param directory:
        :return: None
        """
        for filename in glob.iglob('%s/*.yml' % directory, recursive=False):
            for planner in self.strip_yml(filename):
                await self.dao.create('core_planner', dict(name=planner.get('name'), module=planner.get('module'),
                                                           params=json.dumps(planner.get('params'))))

    """ PERSIST """

    async def persist_ability(self, ability_id, file_contents):
        """
        Save a new ability from either the GUI or REST API. This updates an existing ability, if found, or writes
        a new YML file into the core data/ directory.
        :param ability_id:
        :param file_contents:
        :return:
        """
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % ability_id, location='data')
        if not file_path:
            file_path = 'data/abilities/all/%s.yml' % ability_id
        with open(file_path, 'w+') as f:
            f.seek(0)
            f.write(file_contents)
            f.truncate()

    async def persist_adversary(self, i, name, description, phases):
        """
        Save a new adversary from either the GUI or REST API. This writes a new YML file into the core data/ directory.
        :param i:
        :param name:
        :param description:
        :param phases:
        :return: the ID of the created adversary
        """
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % i, location='data')
        if not file_path:
            file_path = 'data/adversaries/%s.yml' % i
        with open(file_path, 'w+') as f:
            f.seek(0)
            p = defaultdict(list)
            for ability in phases:
                p[ability['phase']].append(ability['id'])
            f.write(yaml.dump(dict(id=i, name=name, description=description, phases=dict(p))))
            f.truncate()
        return await self.create_adversary(i, name, description, phases)

    """ CREATE """

    async def create_ability(self, ability_id, tactic, technique_name, technique_id, name, test, description, executor,
                             platform, cleanup=None, payload=None, parser=None):
        """
        Save a new ability to the database
        :param ability_id:
        :param tactic:
        :param technique_name:
        :param technique_id:
        :param name:
        :param test:
        :param description:
        :param executor:
        :param platform:
        :param cleanup:
        :param payload:
        :param parser:
        :return: the database id
        """
        ability = dict(ability_id=ability_id, name=name, test=test, tactic=tactic,
                       technique_id=technique_id, technique_name=technique_name,
                       executor=executor, platform=platform, description=description,
                       cleanup=cleanup)
        identifier = await self.dao.create('core_ability', ability)
        if payload:
            await self.dao.create('core_payload', dict(ability=identifier, payload=payload))
        if parser:
            parser['ability'] = identifier
            await self.dao.create('core_parser', parser)
        return identifier

    async def create_adversary(self, i, name, description, phases):
        """
        Save a new adversary to the database
        :param i:
        :param name:
        :param description:
        :param phases:
        :return: the database id
        """
        identifier = await self.dao.create('core_adversary',
                                           dict(adversary_id=i, name=name.lower(), description=description))

        await self.dao.delete('core_adversary_map', data=dict(adversary_id=i))
        for ability in phases:
            a = dict(adversary_id=i, phase=ability['phase'], ability_id=ability['id'])
            await self.dao.create('core_adversary_map', a)
        return identifier

    async def create_operation(self, name, group, adversary_id, jitter='2/8', stealth=False, sources=[],
                               planner=None, state=None, allow_untrusted=False):
        """
        Save a new operation to the database
        :param name:
        :param group:
        :param adversary_id:
        :param jitter:
        :param stealth:
        :param sources:
        :param planner:
        :param state:
        :param allow_untrusted:
        :return: the database id
        """
        op_id = await self.dao.create('core_operation', dict(
            name=name, host_group=group, adversary_id=adversary_id, finish=None, phase=0, jitter=jitter,
            start=self.get_current_timestamp(), stealth=stealth, planner=planner, state=state,
            allow_untrusted=allow_untrusted))
        source_id = await self.dao.create('core_source', dict(name=name))
        await self.dao.create('core_source_map', dict(op_id=op_id, source_id=source_id))
        for s_id in [s for s in sources if s]:
            await self.dao.create('core_source_map', dict(op_id=op_id, source_id=s_id))
        return op_id

    async def create_fact(self, property, value, source_id, score=1, set_id=0, link_id=None):
        """
        Save a new fact to the database
        :param property:
        :param value:
        :param source_id:
        :param score:
        :param set_id:
        :param link_id:
        :return: the database id
        """
        return await self.dao.create('core_fact', dict(property=property, value=value, source_id=source_id,
                                                       score=score, set_id=set_id, link_id=link_id))

    async def create_agent(self, agent, executors):
        """
        Save a new agent to the database
        :param agent:
        :param executors:
        :return: the database id
        """
        agent_id = await self.dao.create('core_agent', agent)
        for i, e in enumerate(executors):
            await self.dao.create('core_executor', dict(agent_id=agent_id, executor=e, preferred=1 if i == 0 else 0))
        return agent_id

    async def create(self, table, data):
        """
        Create a new object in the database
        :param table:
        :param data:
        :return: the database id
        """
        return await self.dao.create(table, data)

    """ VIEW """

    async def get(self, table, criteria):
        """
        Get the contents of any table
        :param table:
        :param criteria:
        :return: a list of dictionary results
        """
        return await self.dao.get(table, criteria)

    async def explode_abilities(self, criteria=None):
        """
        Get all - or a filtered list of - abilities, built out with all sub-objects
        :param criteria:
        :return: a list of dictionary results
        """
        abilities = await self.dao.get('core_ability', criteria=criteria)
        for ab in abilities:
            ab['cleanup'] = '' if ab['cleanup'] is None else ab['cleanup']
            ab['parser'] = await self.dao.get('core_parser', dict(ability=ab['id']))
            ab['payload'] = await self.dao.get('core_payload', dict(ability=ab['id']))
        return abilities

    async def explode_adversaries(self, criteria=None):
        """
        Get all - or a filtered list of - adversaries, built out with all sub-objects
        :param criteria:
        :return: a list of dictionary results
        """
        adversaries = await self.dao.get('core_adversary', criteria)
        for adv in adversaries:
            phases = defaultdict(list)
            for t in await self.dao.get('core_adversary_map', dict(adversary_id=adv['adversary_id'])):
                for ability in await self.explode_abilities(dict(ability_id=t['ability_id'])):
                    phases[t['phase']].append(ability)
            adv['phases'] = dict(phases)
        return adversaries

    async def explode_operation(self, criteria=None):
        """
        Get all - or a filtered list of - operations, built out with all sub-objects
        :param criteria:
        :return: a list of dictionary results
        """
        operations = await self.dao.get('core_operation', criteria)
        for op in operations:
            op['chain'] = sorted(await self.explode_chain(criteria=dict(op_id=op['id'])), key=lambda k: k['id'])
            adversaries = await self.explode_adversaries(dict(id=op['adversary_id']))
            op['adversary'] = adversaries[0]
            op['host_group'] = await self.explode_agents(criteria=dict(host_group=op['host_group']))
            sources = await self.dao.get('core_source_map', dict(op_id=op['id']))
            op['facts'] = await self.dao.get_in('core_fact', 'source_id', [s['source_id'] for s in sources])
        return operations

    async def explode_agents(self, criteria: object = None) -> object:
        """
        Get all - or a filtered list of - agents, built out with all sub-objects
        :param criteria:
        :return: a list of dictionary results
        """
        agents = await self.dao.get('core_agent', criteria)
        for a in agents:
            executors = await self.dao.get('core_executor', criteria=dict(agent_id=a['id']))
            a['executors'] = [dict(executor=e['executor'], preferred=e['preferred']) for e in executors]
        return agents

    async def explode_results(self, criteria=None):
        """
        Get all - or a filtered list of - results, built out with all sub-objects
        :param criteria:
        :return: a list of dictionary results
        """
        results = await self.dao.get('core_result', criteria=criteria)
        for r in results:
            link = await self.dao.get('core_chain', dict(id=r['link_id']))
            link[0]['facts'] = await self.dao.get('core_fact', dict(link_id=link[0]['id']))
            r['link'] = link[0]
        return results

    async def explode_chain(self, criteria=None):
        """
        Get all - or a filtered list of - chain links, built out with all sub-objects
        :param criteria:
        :return: a list of dictionary results
        """
        chain = []
        for link in await self.dao.get('core_chain', criteria=criteria):
            a = await self.dao.get('core_ability', criteria=dict(id=link['ability']))
            chain.append(dict(abilityName=a[0]['name'], abilityDescription=a[0]['description'], **link))
        return chain

    async def explode_sources(self, criteria=None):
        """
        Get all - or a filtered list of - sources, built out with all sub-objects
        :param criteria:
        :return: a list of dictionary results
        """
        sources = await self.dao.get('core_source', criteria=criteria)
        for s in sources:
            s['facts'] = await self.dao.get('core_fact', dict(source_id=s['id']))
        return sources

    async def explode_planners(self, criteria=None):
        """
        Get all - or a filtered list of - planners, built out with all sub-objects
        :param criteria:
        :return: a list of dictionary results
        """
        planners = await self.dao.get('core_planner', criteria=criteria)
        for p in planners:
            p['params'] = json.loads(p['params'])
        return planners

    """ DELETE """

    async def delete(self, index, criteria):
        """
        Delete any object in the database by table name and ID
        :param index: the name of the table
        :param criteria: a dict of key/value pairs to match on
        """
        self.log.debug('Deleting %s from %s' % (criteria, index))
        await self.dao.delete(index, data=criteria)

    """ UPDATE """

    async def update(self, table, key, value, data):
        """
        Update any field in any table in the database
        :param table: 
        :param key:
        :param value:
        :param data:
        :return: None
        """
        await self.dao.update(table, key, value, data)
