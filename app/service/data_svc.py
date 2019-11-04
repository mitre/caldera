import asyncio
import glob
import json
import pickle
import os.path
from base64 import b64encode
from collections import defaultdict

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_fact import Fact
from app.objects.c_parser import Parser
from app.objects.c_planner import Planner
from app.objects.c_relationship import Relationship
from app.objects.c_requirement import Requirement
from app.objects.c_source import Source
from app.utility.base_service import BaseService


class DataService(BaseService):

    def __init__(self):
        self.log = self.add_service('data_svc', self)
        self.ram = dict(agents=[], planners=[], adversaries=[], abilities=[], sources=[], operations=[])

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
        if os.path.exists('data/object_store'):
            await asyncio.sleep(3)
            with open('data/object_store', 'rb') as objects:
                ram = pickle.load(objects)
                for key in ram.keys():
                    for c_object in ram[key]:
                        await self.store(c_object)
            self.log.debug('Restored objects from persistent storage')

    async def apply(self, collection):
        """
        Add a new collection to RAM
        :param collection:
        :return:
        """
        self.ram[collection] = []

    async def load_data(self, directory=None):
        """
        Read all the data sources to populate the object store
        :param directory:
        :param schema:
        :return: None
        """
        self.log.debug('Loading data from %s...' % directory)
        await self._load_abilities(directory='%s/abilities' % directory)
        await self._load_adversaries(directory='%s/adversaries' % directory)
        await self._load_sources(directory='%s/facts' % directory)
        await self._load_planners(directory='%s/planners' % directory)

    async def store(self, c_object):
        """
        Accept any c_object type and store it (create/update) in RAM
        :param c_object:
        :return: a single c_object
        """
        try:
            return c_object.store(self.ram)
        except Exception as e:
            self.log.error('[!] can only store first-class objects: %s' % e)

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

    async def _load_adversaries(self, directory):
        total = 0
        for filename in glob.iglob('%s/*.yml' % directory, recursive=True):
            for adv in self.strip_yml(filename):
                phases = [dict(phase=k, id=i) for k, v in adv.get('phases', dict()).items() for i in v]
                ps = []
                for p in adv.get('packs', []):
                    ps.append(await self._add_adversary_packs(p))
                for pack in ps:
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
                                                           privilege=ab['privilege'] if 'privilege' in ab.keys() else
                                                           None)
                                total += 1
        self.log.debug('Loaded %s abilities' % total)

    async def _load_sources(self, directory):
        total = 0
        for filename in glob.iglob('%s/*.yml' % directory, recursive=False):
            for src in self.strip_yml(filename):
                source = Source(
                    name=src['name'],
                    facts=[Fact(trait=f['trait'], value=str(f['value'])) for f in src.get('facts')]
                )
                await self.store(source)
                total += 1
        self.log.debug('Loaded %s sources' % total)

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

    async def _add_adversary_packs(self, pack):
        _, filename = await self.get_service('file_svc').find_file_path('%s.yml' % pack, location='data')
        for adv in self.strip_yml(filename):
            return [dict(phase=k, id=i) for k, v in adv.get('phases').items() for i in v]

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
