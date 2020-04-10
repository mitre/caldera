import asyncio
import copy
import glob
import os.path
import pickle
from base64 import b64encode
from collections import namedtuple

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_planner import Planner
from app.objects.c_plugin import Plugin
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

    async def _link_abilities(self, ordering, adversary):
        try:
            return [v for ab in ordering for v in await self.locate('abilities', match=dict(ability_id=ab))]
        except Exception as e:
            self.log.error('Abilities missing from adversary %s (%s): %s' % (adversary['name'], adversary['id'], e))
            return []

    async def _load(self, plugins=()):
        try:
            if not plugins:
                plugins = [p for p in await self.locate('plugins') if p.data_dir]
                plugins.append(Plugin(data_dir='data'))
            for plug in plugins:
                await self._load_payloads(plug)
                await self._load_abilities(plug)
            await self._verify_ability_set()
            for plug in plugins:
                await self._load_adversaries(plug)
                await self._load_sources(plug)
                await self._load_planners(plug)
        except Exception as e:
            self.log.debug(repr(e))

    async def _load_adversaries(self, plugin):
        for filename in glob.iglob('%s/adversaries/**/*.yml' % plugin.data_dir, recursive=True):
            for adv in self.strip_yml(filename):
                if adv.get('phases'):
                    ordering = await self._load_phase_adversary_variant(adv)
                else:
                    ordering = adv.get('atomic_ordering', list())
                atomic_ordering = await self._link_abilities(ordering, adv)
                adversary = Adversary(adversary_id=adv['id'], name=adv['name'], description=adv['description'],
                                      atomic_ordering=atomic_ordering)
                adversary.access = plugin.access
                await self.store(adversary)

    @staticmethod
    async def _load_phase_adversary_variant(adversary):
        abilities = []
        for v in adversary.get('phases').values():
            abilities.extend(v)
        return abilities

    async def _load_abilities(self, plugin):
        for filename in glob.iglob('%s/abilities/**/*.yml' % plugin.data_dir, recursive=True):
            for entries in self.strip_yml(filename):
                for ab in entries:
                    if ab.get('tactic') and ab.get('tactic') not in filename:
                        self.log.error('Ability=%s has wrong tactic' % ab['id'])
                    for platforms, executors in ab.get('platforms').items():
                        for pl in platforms.split(','):
                            for name, info in executors.items():
                                for e in name.split(','):
                                    technique_name = ab.get('technique', dict()).get('name')
                                    technique_id = ab.get('technique', dict()).get('attack_id')
                                    encoded_test = b64encode(info['command'].strip().encode('utf-8')).decode() if info.get('command') else None
                                    cleanup_cmd = b64encode(info['cleanup'].strip().encode('utf-8')).decode() if info.get('cleanup') else None
                                    a = await self._create_ability(ability_id=ab.get('id'), tactic=ab.get('tactic'),
                                                                   technique_name=technique_name,
                                                                   technique_id=technique_id,
                                                                   test=encoded_test,
                                                                   description=ab.get('description') or '',
                                                                   executor=e, name=ab.get('name'), platform=pl,
                                                                   cleanup=cleanup_cmd,
                                                                   payloads=info.get('payloads'),
                                                                   parsers=info.get('parsers', []),
                                                                   timeout=info.get('timeout', 60),
                                                                   requirements=ab.get('requirements', []),
                                                                   privilege=ab[
                                                                       'privilege'] if 'privilege' in ab.keys() else None,
                                                                   access=plugin.access, repeatable=ab.get('repeatable', False),
                                                                   variations=info.get('variations', []))
                                    await self._update_extensions(a)

    async def _update_extensions(self, ability):
        for ab in await self.locate('abilities', dict(name=None, ability_id=ability.ability_id)):
            ab.name = ability.name
            ab.description = ability.description
            ab.tactic = ability.tactic
            ab.technique_id = ability.technique_id
            ab.technique_name = ability.technique_name
            await self.store(ab)

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

    async def _load_payloads(self, plugin):
        for filename in glob.iglob('%s/payloads/*.yml' % plugin.data_dir, recursive=False):
            data = self.strip_yml(filename)
            payload_config = self.get_config(name='payloads')
            payload_config['standard_payloads'] = data[0]['standard_payloads']
            payload_config['special_payloads'] = data[0]['special_payloads']
            await self._apply_special_payload_hooks(payload_config['special_payloads'])
            self.apply_config(name='payloads', config=payload_config)

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

    async def _create_ability(self, ability_id, tactic=None, technique_name=None, technique_id=None, name=None, test=None,
                              description=None, executor=None, platform=None, cleanup=None, payloads=None, parsers=None,
                              requirements=None, privilege=None, timeout=60, access=None, repeatable=False, variations=None):
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
                          cleanup=cleanup, payloads=payloads, parsers=ps, requirements=rs,
                          privilege=privilege, timeout=timeout, repeatable=repeatable, variations=variations)
        ability.access = access
        return await self.store(ability)

    async def _prune_non_critical_data(self):
        self.ram.pop('plugins')
        self.ram.pop('obfuscators')

    async def _apply_special_payload_hooks(self, special_payloads):
        for k, v in special_payloads.items():
            await self.get_service('file_svc').add_special_payload(k, getattr(self.get_service(v['service']),
                                                                              v['function']))

    async def _verify_ability_set(self):
        payload_cleanup = await self.get_service('data_svc').locate('abilities', dict(ability_id='4cd4eb44-29a7-4259-91ae-e457b283a880'))
        for existing in await self.locate('abilities'):
            if not existing.name:
                existing.name = '(auto-generated)'
                self.log.warning('Fix name for ability: %s' % existing.ability_id)
            if not existing.description:
                existing.description = '(auto-generated)'
                self.log.warning('Fix description for ability: %s' % existing.ability_id)
            if not existing.tactic:
                existing.tactic = '(auto-generated)'
                self.log.warning('Fix tactic for ability: %s' % existing.ability_id)
            if not existing.technique_id:
                existing.technique_id = '(auto-generated)'
                self.log.warning('Fix technique ID for ability: %s' % existing.ability_id)
            if not existing.technique_name:
                existing.technique_name = '(auto-generated)'
                self.log.warning('Fix technique name for ability: %s' % existing.ability_id)
            for payload in existing.payloads:
                payload_name = payload
                if self.is_uuid4(payload):
                    payload_name, _ = self.get_service('file_svc').get_payload_name_from_uuid(payload)
                _, path = await self.get_service('file_svc').find_file_path(payload_name)
                if not path:
                    self.log.error('Payload referenced in %s but not found: %s' % (existing.ability_id, payload))
                    continue
                for clean_ability in [a for a in payload_cleanup if a.executor == existing.executor]:
                    if self.is_uuid4(payload):
                        decoded_test = existing.replace_cleanup(clean_ability.cleanup[0], '#{payload:%s}' % payload)
                    else:  # Explain why the else is here
                        decoded_test = existing.replace_cleanup(clean_ability.cleanup[0], payload)
                    cleanup_command = self.encode_string(decoded_test)
                    if cleanup_command not in existing.cleanup:
                        existing.cleanup.append(cleanup_command)
