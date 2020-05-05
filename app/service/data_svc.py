import asyncio
import copy
import glob
import os.path
import pickle
import shutil
from base64 import b64encode

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_planner import Planner
from app.objects.c_plugin import Plugin
from app.objects.c_source import Source
from app.objects.secondclass.c_parser import Parser
from app.objects.secondclass.c_parserconfig import ParserConfig
from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_requirement import Requirement
from app.service.interfaces.i_data_svc import DataServiceInterface
from app.utility.base_service import BaseService

MIN_MODULE_LEN = 1


class DataService(DataServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('data_svc', self)
        self.schema = dict(agents=[], planners=[], adversaries=[], abilities=[], sources=[], operations=[],
                           schedules=[], plugins=[], obfuscators=[])
        self.ram = copy.deepcopy(self.schema)

    @staticmethod
    async def destroy():
        if os.path.exists('data/object_store'):
            os.remove('data/object_store')
        for d in ['data/results', 'data/adversaries', 'data/abilities', 'data/facts', 'data/sources', 'data/payloads']:
            for f in glob.glob('%s/*' % d):
                if not f.startswith('.'):
                    try:
                        os.remove(f)
                    except IsADirectoryError:
                        shutil.rmtree(f)

    async def save_state(self):
        await self._prune_non_critical_data()
        await self.get_service('file_svc').save_file('object_store', pickle.dumps(self.ram), 'data')

    async def restore_state(self):
        """
        Restore the object database

        :return:
        """
        if os.path.exists('data/object_store'):
            _, store = await self.get_service('file_svc').read_file('object_store', 'data')
            # Pickle is only used to load a local file that caldera creates. Pickled data is not
            # received over the network.
            ram = pickle.loads(store)  # nosec
            for key in ram.keys():
                self.ram[key] = []
                for c_object in ram[key]:
                    await self.store(c_object)
            self.log.debug('Restored data from persistent storage')
        self.log.debug('There are %s jobs in the scheduler' % len(self.ram['schedules']))

    async def apply(self, collection):
        if collection not in self.ram:
            self.ram[collection] = []

    async def load_data(self, plugins=()):
        loop = asyncio.get_event_loop()
        loop.create_task(self._load(plugins))

    async def reload_data(self, plugins=()):
        await self._load(plugins)

    async def store(self, c_object):
        try:
            return c_object.store(self.ram)
        except Exception as e:
            self.log.error('[!] can only store first-class objects: %s' % e)

    async def locate(self, object_name, match=None):
        try:
            return [obj for obj in self.ram[object_name] if obj.match(match)]
        except Exception as e:
            self.log.error('[!] LOCATE: %s' % e)

    async def remove(self, object_name, match):
        try:
            self.ram[object_name][:] = [obj for obj in self.ram[object_name] if not obj.match(match)]
        except Exception as e:
            self.log.error('[!] REMOVE: %s' % e)

    """ PRIVATE """

    async def _load(self, plugins=()):
        try:
            if not plugins:
                plugins = [p for p in await self.locate('plugins') if p.data_dir and p.enabled]
                plugins.append(Plugin(data_dir='data'))
            for plug in plugins:
                await self._load_payloads(plug)
                await self._load_abilities(plug)
            await self._verify_ability_set()
            for plug in plugins:
                await self._load_adversaries(plug)
                await self._load_sources(plug)
                await self._load_planners(plug)
            await self._load_extensions()
        except Exception as e:
            self.log.debug(repr(e), exc_info=True)

    async def _load_adversaries(self, plugin):
        for filename in glob.iglob('%s/adversaries/**/*.yml' % plugin.data_dir, recursive=True):
            for adv in self.strip_yml(filename):
                adversary = Adversary.load(adv)
                adversary.access = plugin.access
                await self.store(adversary)

    async def _load_abilities(self, plugin):
        for filename in glob.iglob('%s/abilities/**/*.yml' % plugin.data_dir, recursive=True):
            for entries in self.strip_yml(filename):
                for ab in entries:
                    if ab.get('tactic') and ab.get('tactic') not in filename:
                        self.log.warning('Ability=%s has wrong tactic' % ab['id'])
                    for platforms, executors in ab.get('platforms').items():
                        for pl in platforms.split(','):
                            for name, info in executors.items():
                                for e in name.split(','):
                                    technique_name = ab.get('technique', dict()).get('name')
                                    technique_id = ab.get('technique', dict()).get('attack_id')
                                    encoded_test = b64encode(info['command'].strip().encode('utf-8')).decode() if info.get('command') else None
                                    cleanup_cmd = b64encode(info['cleanup'].strip().encode('utf-8')).decode() if info.get('cleanup') else None
                                    encoded_code = self.encode_string(info['code'].strip()) if info.get('code') else None
                                    payloads = ab.get('payloads') if encoded_code else info.get('payloads')
                                    a = await self._create_ability(ability_id=ab.get('id'), tactic=ab.get('tactic'),
                                                                   technique_name=technique_name,
                                                                   technique_id=technique_id,
                                                                   test=encoded_test,
                                                                   description=ab.get('description') or '',
                                                                   executor=e, name=ab.get('name'), platform=pl,
                                                                   cleanup=cleanup_cmd,
                                                                   code=encoded_code,
                                                                   language=info.get('language'),
                                                                   build_target=info.get('build_target'),
                                                                   payloads=payloads,
                                                                   parsers=info.get('parsers', []),
                                                                   timeout=info.get('timeout', 60),
                                                                   requirements=ab.get('requirements', []),
                                                                   privilege=ab[
                                                                       'privilege'] if 'privilege' in ab.keys() else None,
                                                                   buckets=await self._classify(ab),
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

    async def _classify(self, ability):
        if 'buckets' in ability:
            return ability['buckets'].lower()
        return [ability['tactic'].lower()]

    async def _load_sources(self, plugin):
        for filename in glob.iglob('%s/sources/*.yml' % plugin.data_dir, recursive=False):
            for src in self.strip_yml(filename):
                source = Source.load(src)
                source.access = plugin.access
                await self.store(source)

    async def _load_payloads(self, plugin):
        for filename in glob.iglob('%s/payloads/*.yml' % plugin.data_dir, recursive=False):
            data = self.strip_yml(filename)
            payload_config = self.get_config(name='payloads')
            payload_config['standard_payloads'] = data[0]['standard_payloads']
            payload_config['special_payloads'] = data[0]['special_payloads']
            payload_config['extensions'] = data[0]['extensions']
            await self._apply_special_payload_hooks(payload_config['special_payloads'])
            await self._apply_special_extension_hooks(payload_config['extensions'])
            self.apply_config(name='payloads', config=payload_config)

    async def _load_planners(self, plugin):
        for filename in glob.iglob('%s/planners/*.yml' % plugin.data_dir, recursive=False):
            for planner in self.strip_yml(filename):
                planner = Planner.load(planner)
                planner.access = plugin.access
                await self.store(planner)

    async def _load_extensions(self):
        for entry in self._app_configuration['payloads']['extensions']:
            await self.get_service('file_svc').add_special_payload(entry,
                                                                   self._app_configuration['payloads']
                                                                   ['extensions'][entry])

    async def _create_ability(self, ability_id, tactic=None, technique_name=None, technique_id=None, name=None, test=None,
                              description=None, executor=None, platform=None, cleanup=None, payloads=None, parsers=None,
                              requirements=None, privilege=None, timeout=60, access=None, buckets=None, repeatable=False,
                              code=None, language=None, build_target=None, variations=None):
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
                          technique_id=technique_id, technique=technique_name, code=code, language=language,
                          executor=executor, platform=platform, description=description, build_target=build_target,
                          cleanup=cleanup, payloads=payloads, parsers=ps, requirements=rs,
                          privilege=privilege, timeout=timeout, repeatable=repeatable,
                          variations=variations, buckets=buckets)
        ability.access = access
        return await self.store(ability)

    async def _prune_non_critical_data(self):
        self.ram.pop('plugins')
        self.ram.pop('obfuscators')

    async def _apply_special_extension_hooks(self, special_extensions):
        for k, v in special_extensions.items():
            if len(v.split('.')) > MIN_MODULE_LEN:
                try:
                    mod = __import__('.'.join(v.split('.')[:-1]), fromlist=[v.split('.')[-1]])
                    handle = getattr(mod, v.split('.')[-1])
                    self.get_service('file_svc').special_payloads[k] = handle
                except AttributeError:
                    self.log.error('Unable to properly load {} for payload {} from string.'.format(k, v))
                except ModuleNotFoundError:
                    self.log.warning('Unable to properly load {} for payload {} due to failed import'.format(k, v))
            else:
                self.log.warning('Unable to decipher target function from string {}.'.format(v))

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
                    self.log.warning('Payload referenced in %s but not found: %s' % (existing.ability_id, payload))
                    continue
                for clean_ability in [a for a in payload_cleanup if a.executor == existing.executor]:
                    if self.is_uuid4(payload):
                        decoded_test = existing.replace_cleanup(clean_ability.cleanup[0], '#{payload:%s}' % payload)
                    else:  # Explain why the else is here
                        decoded_test = existing.replace_cleanup(clean_ability.cleanup[0], payload)
                    cleanup_command = self.encode_string(decoded_test)
                    if cleanup_command not in existing.cleanup:
                        existing.cleanup.append(cleanup_command)
