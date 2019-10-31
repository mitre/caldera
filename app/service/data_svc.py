import asyncio
import glob
import json
import pickle

from base64 import b64encode
from collections import defaultdict

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_parser import Parser
from app.objects.c_planner import Planner
from app.objects.c_relationship import Relationship
from app.objects.c_requirement import Requirement
from app.service.base_service import BaseService
from app.utility.rule import RuleAction


class DataService(BaseService):

    def __init__(self, dao):
        self.dao = dao
        self.log = self.add_service('data_svc', self)
        self.ram = dict(agents=[], planners=[], adversaries=[], abilities=[])

    async def save_state(self):
        """
        Save RAM database to file
        :return:
        """
        with open('data/object_store', 'wb') as objects:
            pickle.dump(self.ram, objects)

    async def restore_state(self):
        """
        Restore the object database - but wait for YML files to load first
        :return:
        """
        await asyncio.sleep(3)
        with open('data/object_store', 'rb') as objects:
            ram = pickle.load(objects)
            [await self.store(x) for x in ram['agents']]
            [await self.store(x) for x in ram['planners']]
            [await self.store(x) for x in ram['abilities']]
            [await self.store(x) for x in ram['adversaries']]
        self.log.debug('Restored objects from persistent storage')

    async def apply(self, collection):
        """
        Add a new collection to RAM
        :param collection:
        :return:
        """
        self.ram[collection] = []

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
            self.log.debug('Loading data from %s...' % directory)
            await self._load_abilities(directory='%s/abilities' % directory)
            await self._load_adversaries(directory='%s/adversaries' % directory)
            await self._load_facts(directory='%s/facts' % directory)
            await self._load_planners(directory='%s/planners' % directory)

    async def save(self, object_name, object_dict):
        """
        Save a dict() for any object
        :param object_name:
        :param object_dict:
        :return:
        """
        try:
            if object_name == 'operation':
                return await self._create_operation(**object_dict)
            elif object_name == 'link':
                return await self._create_link(object_dict)
            elif object_name == 'relationship':
                return await self.dao.create('core_relationship', object_dict)
            elif object_name == 'fact':
                return await self.dao.create('core_fact', object_dict)
            elif object_name == 'result':
                return await self.dao.create('core_result', object_dict)
            self.log.warning('[!] SAVE on non-core type: %s' % object_name)
            return await self.dao.create(object_name, object_dict)
        except Exception as e:
            self.log.error('[!] SAVE %s: %s' % (object_name, e))

    async def delete(self, object_name, criteria):
        """
        Delete any object in the database by table name and ID
        :param object_name: the name of the table
        :param criteria: a dict of key/value pairs to match on
        """
        self.log.debug('Deleting %s from %s' % (criteria, object_name))
        await self.dao.delete('core_%s' % object_name, data=criteria)

    async def update(self, object_name, key, value, data):
        """
        Update any field in any table in the database
        :param object_name:
        :param key:
        :param value:
        :param data:
        :return: None
        """
        await self.dao.update('core_%s' % object_name, key, value, data)

    async def get(self, object_name, criteria=None):
        """
        Get the contents of any object
        :param object_name:
        :param criteria:
        :return: a list of dictionary results
        """
        try:
            if object_name == 'operation':
                return await self.dao.get('core_operation', criteria)
            elif object_name == 'chain':
                return await self.dao.get('core_chain', criteria)
            elif object_name == 'used':
                return await self.dao.get('core_used', criteria)
            elif object_name == 'fact':
                return await self.dao.get('core_fact', criteria)
            self.log.warning('[!] GET on non-core type: %s' % object_name)
            return await self.dao.get(object_name, criteria)
        except Exception as e:
            self.log.error('[!] GET %s: %s' % (object_name, e))

    async def explode(self, object_name, criteria=None):
        """
        Get an exploded version of any object
        :param object_name:
        :param criteria:
        :return:
        """
        try:
            if object_name == 'operation':
                return await self._explode_operation(criteria)
            elif object_name == 'chain':
                return await self._explode_chain(criteria)
            elif object_name == 'source':
                return await self._explode_sources(criteria)
            elif object_name == 'result':
                return await self._explode_results(criteria)
            elif object_name == 'used':
                return await self._explode_used(criteria)
            self.log.error('[!] EXPLODE on unknown type: %s' % object_name)
        except Exception as e:
            self.log.error('[!] EXPLODE %s: %s' % (object_name, e))

    async def store(self, c_object):
        """
        Accept any c_object type and store it (create/update) in RAM
        :param c_object:
        :return: a single c_object
        """
        try:
            return c_object.store(self.ram)
        except Exception as e:
            self.log.error('[!] STORE: %s' % e)

    async def locate(self, object_name, match=None):
        """
        Find all c_objects which match a search. Return all c_objects if no match.
        :param object_name:
        :param match: dict()
        :return: a list of c_object types
        """
        try:
            return [obj for obj in self.ram[object_name] if obj.match(match)]
        except Exception as e:
            self.log.error('[!] LOCATE: %s' % e)

    async def remove(self, object_name, match):
        """
        Remove any c_objects which match a search
        :param object_name:
        :param match: dict()
        :return:
        """
        try:
            self.ram[object_name][:] = [obj for obj in self.ram[object_name] if not obj.match(match)]
        except Exception as e:
            self.log.error('[!] REMOVE: %s' % e)

    """ PRIVATE """

    async def _explode_operation(self, criteria=None):
        operations = await self.dao.get('core_operation', criteria)
        for op in operations:
            op['chain'] = sorted(await self._explode_chain(criteria=dict(op_id=op['id'])), key=lambda k: k['id'])
            adversaries = await self.locate('adversaries', match=dict(adversary_id=op['adversary_id']))
            op['adversary'] = adversaries[0]
            op['host_group'] = await self.locate('agents', match=dict(group=op['host_group']))
            sources = await self.dao.get('core_source_map', dict(op_id=op['id']))
            source_list = [s['source_id'] for s in sources]
            op['facts'] = await self.dao.get_in('core_fact', 'source_id', source_list)
            for fact in op['facts']:
                fact['relationships'] = await self._add_fact_relationships(dict(source=fact['id']))
            op['rules'] = await self._sort_rules_by_fact(await self.dao.get_in('core_rule', 'source_id', source_list))
        return operations

    async def _explode_results(self, criteria=None):
        results = await self.dao.get('core_result', criteria=criteria)
        for r in results:
            link = await self.dao.get('core_chain', dict(id=r['link_id']))
            link[0]['facts'] = await self.dao.get('core_fact', dict(link_id=link[0]['id']))
            r['link'] = link[0]
        return results

    async def _explode_chain(self, criteria=None):
        chain = []
        for link in await self.dao.get('core_chain', criteria=criteria):
            a = await self.locate('abilities', match=dict(unique=link['ability']))
            chain.append(dict(abilityName=a[0].name, abilityDescription=a[0].description, **link))
        return chain

    async def _explode_sources(self, criteria=None):
        sources = await self.dao.get('core_source', criteria=criteria)
        for s in sources:
            s['facts'] = await self.dao.get('core_fact', dict(source_id=s['id']))
        return sources

    async def _explode_used(self, criteria=None):
        used_facts = await self.dao.get('core_used', criteria=criteria)
        for uf in used_facts:
            fact = (await self.dao.get('core_fact', dict(id=uf['fact_id'])))[0]
            uf['property'] = fact['property']
            uf['value'] = fact['value']
        return used_facts

    async def _create_link(self, link):
        used = link.pop('used', [])
        link_id = await self.dao.create('core_chain', link)
        for uf in used:
            await self.dao.create('core_used', dict(link_id=link_id, fact_id=uf))

    async def _create_adversary(self, i, name, description, phases):
        identifier = await self.dao.create('core_adversary',
                                           dict(adversary_id=i, name=name, description=description))

        await self.dao.delete('core_adversary_map', data=dict(adversary_id=i))
        for ability in phases:
            a = dict(adversary_id=i, phase=ability['phase'], ability_id=ability['id'])
            await self.dao.create('core_adversary_map', a)
        return identifier

    async def _load_facts(self, directory):
        total = 0
        for filename in glob.iglob('%s/*.yml' % directory, recursive=False):
            for source in self.strip_yml(filename):
                source_id = await self.dao.create('core_source', dict(name=source['name']))
                for fact in source.get('facts', []):
                    fact['source_id'] = source_id
                    fact['score'] = fact.get('score', 1)
                    await self.save('fact', fact)
                for rule in source.get('rules', []):
                    rule['source_id'] = source_id
                    await self._create_rule(**rule)
                total += 1
        self.log.debug('Loaded %s fact sources' % total)

    async def _load_planners(self, directory):
        total = 0
        for filename in glob.iglob('%s/*.yml' % directory, recursive=False):
            for planner in self.strip_yml(filename):
                await self.store(
                    Planner(name=planner.get('name'), module=planner.get('module'),
                            params=json.dumps(planner.get('params')))
                )
                total += 1
        self.log.debug('Loaded %s planners' % total)

    async def _create_rule(self, fact, source_id, action='DENY', match='.*'):
        try:
            action = RuleAction[action.upper()].value
            await self.dao.create('core_rule', dict(fact=fact, source_id=source_id, action=action, match=match))
        except KeyError:
            self.log.error(
                'Rule action must be in [%s] not %s' % (', '.join(RuleAction.__members__.keys()), action.upper()))

    @staticmethod
    async def _sort_rules_by_fact(rules):
        organized_rules = defaultdict(list)
        for rule in rules:
            fact = rule.pop('fact')
            organized_rules[fact].append(rule)
        return organized_rules

    async def _save_ability_extras(self, identifier, payload, parsers, requirements):
        if payload:
            await self.dao.create('core_payload', dict(ability=identifier, payload=payload))
        await self._save_ability_relationships(identifier, table='core_parser', id_type='parser_id',
                                               relationships=parsers)
        await self._save_ability_relationships(identifier, table='core_requirement', id_type='requirement_id',
                                               relationships=requirements)
        return identifier

    async def _save_ability_relationships(self, identifier, table, id_type, relationships):
        for module in relationships:
            _id = await self.dao.create(table, dict(ability=identifier, module=module))
            for r in relationships.get(module):
                relationship = {id_type: _id, 'source': r.get('source'), 'edge': r.get('edge'),
                                'target': r.get('target')}
                await self.dao.create('%s_map' % table, relationship)

    async def _add_adversary_packs(self, pack):
        _, filename = await self.get_service('file_svc').find_file_path('%s.yml' % pack, location='data')
        for adv in self.strip_yml(filename):
            return [dict(phase=k, id=i) for k, v in adv.get('phases').items() for i in v]

    async def _add_fact_relationships(self, criteria=None):
        relationships = await self.dao.get('core_relationship', criteria)
        return [dict(edge=r.get('edge'), target=(await self.dao.get('core_fact', dict(id=r.get('target'))))[0])
                for r in relationships if r.get('target')]

    async def _create_operation(self, name, group, adversary_id, jitter='2/8', sources=[],
                                planner=None, state=None, allow_untrusted=False, autonomous=True):
        op_id = await self.dao.create('core_operation', dict(
            name=name, host_group=group, adversary_id=adversary_id, finish=None, phase=0, jitter=jitter,
            start=self.get_current_timestamp(), planner=planner, state=state,
            allow_untrusted=allow_untrusted, autonomous=autonomous))
        source_id = await self.dao.create('core_source', dict(name=name))
        await self.dao.create('core_source_map', dict(op_id=op_id, source_id=source_id))
        for s_id in [s for s in sources if s]:
            await self.dao.create('core_source_map', dict(op_id=op_id, source_id=s_id))
        return op_id

    async def _load_adversaries(self, directory):
        total = 0
        for filename in glob.iglob('%s/*.yml' % directory, recursive=True):
            for adv in self.strip_yml(filename):
                phases = [dict(phase=k, id=i) for k, v in adv.get('phases', dict()).items() for i in v]
                for pack in [await self._add_adversary_packs(p) for p in adv.get('packs', [])]:
                    phases += pack
                if adv.get('visible', True):
                    pp = defaultdict(list)
                    for phase in phases:
                        for ability in await self.locate('abilities', match=dict(ability_id=phase['id'])):
                            pp[phase['phase']].append(ability)
                    phases = dict(pp)
                    await self.store(
                        Adversary(adversary_id=adv['id'], name=adv['name'], description=adv['description'],
                                  phases=phases)
                    )
                    total += 1
        self.log.debug('Loaded %s adversaries' % total)

    async def _load_abilities(self, directory):
        total = 0
        for filename in glob.iglob('%s/**/*.yml' % directory, recursive=True):
            for entries in self.strip_yml(filename):
                for ab in entries:
                    for pl, executors in ab['platforms'].items():
                        for name, info in executors.items():
                            for e in name.split(','):
                                encoded_test = b64encode(info['command'].strip().encode('utf-8'))
                                await self._create_ability(ability_id=ab.get('id'), tactic=ab['tactic'].lower(),
                                                           technique_name=ab['technique']['name'],
                                                           technique_id=ab['technique']['attack_id'],
                                                           test=encoded_test.decode(),
                                                           description=ab.get('description') or '',
                                                           executor=e, name=ab['name'], platform=pl,
                                                           cleanup=b64encode(
                                                               info['cleanup'].strip().encode(
                                                                   'utf-8')).decode() if info.get(
                                                               'cleanup') else None,
                                                           payload=info.get('payload'), parsers=info.get('parsers', []),
                                                           requirements=ab.get('requirements', []),
                                                           privilege=ab['privilege'] if "privilege" in ab.keys()
                                                           else None)
                                total += 1
        self.log.debug('Loaded %s abilities' % total)

    async def _create_ability(self, ability_id, tactic, technique_name, technique_id, name, test, description, executor,
                              platform, cleanup=None, payload=None, parsers=None, requirements=None, privilege=None):
        ps = []
        for module in parsers:
            relation = [Relationship(source=r['source'], edge=r.get('edge'), target=r.get('target')) for r in
                        parsers[module]]
            ps.append(Parser(module=module, relationships=relation))
        rs = []
        for module in requirements:
            relation = [Relationship(source=r['source'], edge=r.get('edge'), target=r.get('target')) for r in
                        requirements[module]]
            rs.append(Requirement(module=module, relationships=relation))
        await self.store(Ability(ability_id=ability_id, name=name, test=test, tactic=tactic,
                                 technique_id=technique_id, technique=technique_name,
                                 executor=executor, platform=platform, description=description,
                                 cleanup=cleanup, payload=payload, parsers=ps, requirements=rs, privilege=privilege))
