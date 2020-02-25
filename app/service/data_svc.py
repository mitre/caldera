import asyncio
import copy
import glob
import os.path
import pickle
from base64 import b64encode
from collections import defaultdict, namedtuple

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_planner import Planner
from app.objects.c_source import Source
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_parser import Parser
from app.objects.secondclass.c_parserconfig import ParserConfig
from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_requirement import Requirement
from app.objects.secondclass.c_rule import Rule
from app.utility.base_service import BaseService

Adjustment = namedtuple('Adjustment', 'ability_id trait value offset')


class DataService(BaseService):

    def __init__(self):
        self.log = self.add_service('data_svc', self)
        self.schema = dict(agents=[], planners=[], adversaries=[], abilities=[], sources=[], operations=[],
                           schedules=[], plugins=[], obfuscators=[])
        self.ram = copy.deepcopy(self.schema)

    @staticmethod
    async def destroy():
        """
        Clear out all data

        :return:
        """
        if os.path.exists('data/object_store'):
            os.remove('data/object_store')
        for d in ['data/results', 'data/adversaries', 'data/abilities', 'data/facts', 'data/sources']:
            for f in glob.glob('%s/*' % d):
                if not f.startswith('.'):
                    os.remove(f)

    async def save_state(self):
        """
        Save RAM database to file

        :return:
        """
        await self._prune_non_critical_data()
        await self.get_service('file_svc').save_file('object_store', pickle.dumps(self.ram), 'data')

    async def restore_state(self):
        """
        Restore the object database

        :return:
        """
        if os.path.exists('data/object_store'):
            _, store = await self.get_service('file_svc').read_file('object_store', 'data')
            ram = pickle.loads(store)
            for key in ram.keys():
                self.ram[key] = []
                for c_object in ram[key]:
                    await self.store(c_object)
            self.log.debug('Restored data from persistent storage')
        self.log.debug('There are %s jobs in the scheduler' % len(self.ram['schedules']))

    async def apply(self, collection):
        """
        Add a new collection to RAM

        :param collection:
        :return:
        """
        if collection not in self.ram:
            self.ram[collection] = []

    async def load_data(self, plugins=()):
        """
        Non-blocking read all the data sources to populate the object store

        :return: None
        """
        loop = asyncio.get_event_loop()
        loop.create_task(self._load(plugins))

    async def reload_data(self, plugins=()):
        """
        Blocking read all the data sources to populate the object store

        :return: None
        """
        await self._load(plugins)

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

    @staticmethod
    async def _add_phase_abilities(phase_dict, phase, phase_entries):
        for ability in phase_entries:
            phase_dict[phase].append(ability)
        return phase_dict

    async def _insert_pack_phases(self, pack, phases, current_phase, adversary):
        phases_new = await self._add_adversary_packs(pack)
        if phases_new:
            for i, phase in phases_new.items():
                phases.insert(current_phase + i, phase)
            return current_phase + i
        else:
            self.log.error(
                'Missing ability or pack (%s) for adversary: %s (%s)' % (pack, adversary['name'], adversary['id']))
            return 0

    async def _add_phases(self, phases, adversary):
        pp = defaultdict(list)
        phase_id = 0
        while phase_id < len(phases):
            for idx, step in enumerate(phases[phase_id]):
                abilities = await self.locate('abilities', match=dict(ability_id=step))
                if abilities:
                    await self._add_phase_abilities(pp, phase_id + 1, abilities)
                else:
                    # insert this phase and shift down later abilities to new phase
                    del phases[phase_id][idx]
                    last_phase = await self._insert_pack_phases(step, phases, phase_id, adversary)
                    if last_phase and idx < len(phases[phase_id]):
                        phases.insert(last_phase + 1, [phases[phase_id][idx]])
                        del phases[phase_id][idx + 1:]
            phase_id += 1
        return dict(pp)

    async def _load(self, plugins=()):
        try:
            if not plugins:
                plugins = [p for p in await self.locate('plugins') if p.data_dir]
            for plug in plugins:
                await self._load_abilities(plug)
            for plug in plugins:
                await self._load_adversaries(plug)
                await self._load_sources(plug)
                await self._load_planners(plug)
        except Exception as e:
            self.log.debug(repr(e))

    async def _load_adversaries(self, plugin):
        for filename in glob.iglob('%s/adversaries/**/*.yml' % plugin.data_dir, recursive=True):
            for adv in self.strip_yml(filename):
                phases = adv.get('phases', dict())
                for p in adv.get('packs', []):
                    adv_pack = await self._add_adversary_packs(p)
                    if adv_pack:
                        await self._merge_phases(phases, adv_pack)
                sorted_phases = [phases[x] for x in sorted(phases.keys())]
                phases = await self._add_phases(sorted_phases, adv)
                adversary = Adversary(adversary_id=adv['id'], name=adv['name'], description=adv['description'],
                                      phases=phases)
                adversary.access = plugin.access
                await self.store(adversary)

    async def _load_abilities(self, plugin):
        for filename in glob.iglob('%s/abilities/**/*.yml' % plugin.data_dir, recursive=True):
            for entries in self.strip_yml(filename):
                for ab in entries:
                    saved = set()
                    if ab['tactic'] not in filename:
                        self.log.error('Ability=%s has wrong tactic' % ab['id'])
                    for pl, executors in ab['platforms'].items():
                        for name, info in executors.items():
                            for e in name.split(','):
                                encoded_test = b64encode(info['command'].strip().encode('utf-8'))
                                a = await self._create_ability(ability_id=ab.get('id'), tactic=ab['tactic'].lower(),
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
                                                               timeout=info.get('timeout', 60),
                                                               requirements=ab.get('requirements', []),
                                                               privilege=ab[
                                                                   'privilege'] if 'privilege' in ab.keys() else None,
                                                               access=plugin.access, repeatable=ab.get('repeatable', False))
                                saved.add(a.unique)
                    for existing in await self.locate('abilities', match=dict(ability_id=ab['id'])):
                        if existing.unique not in saved:
                            self.log.debug('Ability no longer exists on disk, removing: %s' % existing.unique)
                            await self.remove('abilities', match=dict(unique=existing.unique))
                        if existing.payload:
                            payloads = existing.payload.split(',')
                            for payload in payloads:
                                _, path = await self.get_service('file_svc').find_file_path(payload)
                                if not path:
                                    self.log.error('Payload referenced in %s but not found: %s' %
                                                   (existing.ability_id, payload))

    async def _load_sources(self, plugin):
        for filename in glob.iglob('%s/sources/*.yml' % plugin.data_dir, recursive=False):
            for src in self.strip_yml(filename):
                source = Source(
                    identifier=src['id'],
                    name=src['name'],
                    facts=[Fact(trait=f['trait'], value=str(f['value'])) for f in src.get('facts')],
                    adjustments=await self._create_adjustments(src.get('adjustments')),
                    rules=[Rule(**r) for r in src.get('rules', [])]
                )
                source.access = plugin.access
                await self.store(source)

    async def _load_planners(self, plugin):
        for filename in glob.iglob('%s/planners/*.yml' % plugin.data_dir, recursive=False):
            for planner in self.strip_yml(filename):
                planner = Planner(planner_id=planner.get('id'), name=planner.get('name'), module=planner.get('module'),
                                  params=str(planner.get('params')), description=planner.get('description'),
                                  stopping_conditions=planner.get('stopping_conditions'),
                                  ignore_enforcement_modules=planner.get('ignore_enforcement_modules', ()))
                planner.access = plugin.access
                await self.store(planner)

    @staticmethod
    async def _create_adjustments(raw_adjustments):
        x = []
        if raw_adjustments:
            for ability_id, adjustments in raw_adjustments.items():
                for trait, block in adjustments.items():
                    for change in block:
                        x.append(Adjustment(ability_id, trait, change.get('value'), change.get('offset')))
        return x

    @staticmethod
    async def _merge_phases(phases, new_phases):
        for phase, ids in new_phases.items():
            if phase in phases:
                phases[phase].extend(ids)
            else:
                phases[phase] = ids

    async def _add_adversary_packs(self, pack):
        _, filename = await self.get_service('file_svc').find_file_path('%s.yml' % pack,
                                                                        location=os.path.join('data', 'adversaries'))
        if filename is None:
            return {}
        for adv in self.strip_yml(filename):
            return adv.get('phases')

    async def _create_ability(self, ability_id, tactic, technique_name, technique_id, name, test, description,
                              executor, platform, cleanup=None, payload=None, parsers=None, requirements=None,
                              privilege=None, timeout=60, access=None, repeatable=False):
        ps = []
        for module in parsers:
            pcs = [(ParserConfig(**m)) for m in parsers[module]]
            ps.append(Parser(module=module, parserconfigs=pcs))
        rs = []
        for requirement in requirements:
            for module in requirement:
                relation = [Relationship(source=r['source'], edge=r.get('edge'), target=r.get('target')) for r in
                            requirement[module]]
                rs.append(Requirement(module=module, relationships=relation))
        ability = Ability(ability_id=ability_id, name=name, test=test, tactic=tactic,
                          technique_id=technique_id, technique=technique_name,
                          executor=executor, platform=platform, description=description,
                          cleanup=cleanup, payload=payload, parsers=ps, requirements=rs,
                          privilege=privilege, timeout=timeout, repeatable=repeatable)
        ability.access = access
        return await self.store(ability)

    async def _prune_non_critical_data(self):
        self.ram.pop('plugins')
        self.ram.pop('obfuscators')
