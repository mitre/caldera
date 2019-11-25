import asyncio
import copy
import glob
import json
import os.path
import pickle

from base64 import b64encode
from collections import defaultdict
from importlib import import_module

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_fact import Fact
from app.objects.c_rule import Rule
from app.objects.c_parser import Parser
from app.objects.c_parserconfig import ParserConfig
from app.objects.c_planner import Planner
from app.objects.c_relationship import Relationship
from app.objects.c_requirement import Requirement
from app.objects.c_source import Source
from app.utility.base_service import BaseService


class DataService(BaseService):

    def __init__(self):
        self.log = self.add_service('data_svc', self)
        self.data_dirs = set()
        self.schema = dict(agents=[], planners=[], adversaries=[], abilities=[], sources=[], operations=[],
                           schedules=[], c2=[], plugins=[])
        self.ram = copy.deepcopy(self.schema)

    @staticmethod
    async def destroy():
        """
        Clear out all data
        :return:
        """
        if os.path.exists('data/object_store'):
            os.remove('data/object_store')
        for f in glob.glob('data/results/*'):
            if not f.startswith('.'):
                os.remove(f)

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
            with open('data/object_store', 'rb') as objects:
                ram = pickle.load(objects)
                for key in ram.keys():
                    if key in self.schema:
                        for c_object in ram[key]:
                            await self.store(c_object)
            self.log.debug('Restored objects from persistent storage')
        self.log.debug('There are %s jobs in the scheduler' % len(self.ram['schedules']))

    async def apply(self, collection):
        """
        Add a new collection to RAM
        :param collection:
        :return:
        """
        self.ram[collection] = []

    async def load_data(self, directory=None, poll=False):
        """
        Read all the data sources to populate the object store
        :param directory:
        :return: None
        """
        loop = asyncio.get_event_loop()
        if poll:
            loop.create_task(self._load_abilities(directory='%s/abilities' % directory))
            loop.create_task(self._load_adversaries(directory='%s/adversaries' % directory))
        else:
            loop.create_task(self._load_abilities(directory='%s/abilities' % directory))
            loop.create_task(self._load_adversaries(directory='%s/adversaries' % directory))
            loop.create_task(self._load_sources(directory='%s/facts' % directory))
            loop.create_task(self._load_planners(directory='%s/planners' % directory))
            loop.create_task(self._load_c2(directory='%s/c2' % directory))
            self.data_dirs.add(directory)

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

    async def print_statistics(self):
        """
        Print out the statistics for all objects in the store
        :return:
        """
        for key in self.ram.keys():
            self.log.debug('%s loaded: %s' % (key, len(self.ram[key])))

    """ PRIVATE """

    async def _load_adversaries(self, directory):
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
                        matching_abilities = await self.locate('abilities', match=dict(ability_id=phase['id']))
                        if not len(matching_abilities):
                            self.log.error('Missing Ability (%s) for adversary: %s' % (phase['id'], adv['name']))
                        for ability in matching_abilities:
                            pp[phase['phase']].append(ability)
                    phases = dict(pp)
                    await self.store(
                        Adversary(adversary_id=adv['id'], name=adv['name'], description=adv['description'],
                                  phases=phases)
                    )

    async def _load_abilities(self, directory):
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
                                                           payload=info.get('payload'),
                                                           parsers=info.get('parsers', []),
                                                           requirements=ab.get('requirements', []),
                                                           privilege=ab['privilege'] if 'privilege' in ab.keys() else
                                                           None)

    async def _load_c2(self, directory):
        for filename in glob.iglob('%s/*.yml' % directory, recursive=False):
            for c2 in self.strip_yml(filename):
                module = import_module(c2.get('module'))
                c2_obj = getattr(module, c2.get('name'))(services=self.get_services(), module=c2.get('module'),
                                                         config=c2.get('config'), name=c2.get('name'))
                if not c2_obj.valid_config():
                    self.log.error('C2 channel (%s) does not have a valid configuration. Skipping!' % c2.get('name'))
                    continue
                await self.store(c2_obj)

    async def _load_sources(self, directory):
        for filename in glob.iglob('%s/*.yml' % directory, recursive=False):
            for src in self.strip_yml(filename):
                source = Source(
                    name=src['name'],
                    facts=[Fact(trait=f['trait'], value=str(f['value'])) for f in src.get('facts')],
                    rules=[Rule(**r) for r in src.get('rules')]
                )
                await self.store(source)

    async def _load_planners(self, directory):
        for filename in glob.iglob('%s/*.yml' % directory, recursive=False):
            for planner in self.strip_yml(filename):
                await self.store(
                    Planner(name=planner.get('name'), module=planner.get('module'),
                            params=json.dumps(planner.get('params')))
                )

    async def _add_adversary_packs(self, pack):
        _, filename = await self.get_service('file_svc').find_file_path('%s.yml' % pack, location='data')
        for adv in self.strip_yml(filename):
            return [dict(phase=k, id=i) for k, v in adv.get('phases').items() for i in v]

    async def _create_ability(self, ability_id, tactic, technique_name, technique_id, name, test, description,
                              executor, platform, cleanup=None, payload=None, parsers=None, requirements=None,
                              privilege=None):
        ps = []
        for module in parsers:
            pcs = [(ParserConfig(**m)) for m in parsers[module]]
            ps.append(Parser(module=module, parserconfigs=pcs))
        rs = []
        for module in requirements:
            relation = [Relationship(source=r['source'], edge=r.get('edge'), target=r.get('target')) for r in
                        requirements[module]]
            rs.append(Requirement(module=module, relationships=relation))
        await self.store(Ability(ability_id=ability_id, name=name, test=test, tactic=tactic,
                                 technique_id=technique_id, technique=technique_name,
                                 executor=executor, platform=platform, description=description,
                                 cleanup=cleanup, payload=payload, parsers=ps, requirements=rs, privilege=privilege))
