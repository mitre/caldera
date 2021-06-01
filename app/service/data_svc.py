import asyncio
import copy
import datetime
import glob
import os
import pickle
import tarfile
import shutil
import warnings
from importlib import import_module

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_objective import Objective
from app.objects.c_planner import Planner
from app.objects.c_plugin import Plugin
from app.objects.c_source import Source
from app.objects.secondclass.c_executor import Executor
from app.objects.secondclass.c_goal import Goal
from app.objects.secondclass.c_parser import Parser
from app.objects.secondclass.c_requirement import Requirement
from app.service.interfaces.i_data_svc import DataServiceInterface
from app.utility.base_service import BaseService

MIN_MODULE_LEN = 1

DATA_BACKUP_DIR = "data/backup"
DATA_FILE_GLOBS = (
    'data/abilities/*',
    'data/adversaries/*',
    'data/facts/*',
    'data/objectives/*',
    'data/payloads/*',
    'data/results/*',
    'data/sources/*',
    'data/object_store',
)


class DataService(DataServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('data_svc', self)
        self.schema = dict(agents=[], planners=[], adversaries=[], abilities=[], sources=[], operations=[],
                           schedules=[], plugins=[], obfuscators=[], objectives=[], data_encoders=[])
        self.ram = copy.deepcopy(self.schema)

    @staticmethod
    def _iter_data_files():
        """Yield paths to data files managed by caldera.

        The files paths are relative to the root caldera folder, so they
        will begin with "data/".

        Note:
            This will skip any files starting with '.' (e.g., '.gitkeep').
        """
        for data_glob in DATA_FILE_GLOBS:
            for f in glob.glob(data_glob):
                yield f

    @staticmethod
    def _delete_file(path):
        if not os.path.exists(path):
            return
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    @staticmethod
    async def destroy():
        """Reset the caldera data directory and server state.

        This creates a gzipped tarball backup of the data files tracked by caldera.
        Paths are preserved within the tarball, with all files having "data/" as the
        root.
        """
        if not os.path.exists(DATA_BACKUP_DIR):
            os.mkdir(DATA_BACKUP_DIR)

        timestamp = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
        tarball_path = os.path.join(DATA_BACKUP_DIR, f'backup-{timestamp}.tar.gz')

        with tarfile.open(tarball_path, 'w:gz') as tarball:
            for file_path in DataService._iter_data_files():
                tarball.add(file_path)
                DataService._delete_file(file_path)

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

    async def search(self, value, object_name):
        try:
            return [obj for obj in self.ram[object_name] if obj.search_tags(value)]
        except Exception as e:
            self.log.error('[!] SEARCH: %s' % e)

    async def remove(self, object_name, match):
        try:
            self.ram[object_name][:] = [obj for obj in self.ram[object_name] if not obj.match(match)]
        except Exception as e:
            self.log.error('[!] REMOVE: %s' % e)

    async def load_ability_file(self, filename, access):
        for entries in self.strip_yml(filename):
            for ab in entries:
                ability_id = ab.pop('id', None)
                name = ab.pop('name', '')
                description = ab.pop('description', '')
                tactic = ab.pop('tactic', None)
                technique_id = ab.get('technique', dict()).get('attack_id')
                technique_name = ab.pop('technique', dict()).get('name')
                privilege = ab.pop('privilege', None)
                repeatable = ab.pop('repeatable', False)
                singleton = ab.pop('singleton', False)
                requirements = await self._load_ability_requirements(ab.pop('requirements', []))
                buckets = ab.pop('buckets', [tactic])
                executors = await self.load_executors_from_platform_dict(ab.pop('platforms', dict()))

                if tactic and tactic not in filename:
                    self.log.error('Ability=%s has wrong tactic' % id)

                await self._create_ability(ability_id=ability_id, name=name, description=description, tactic=tactic,
                                           technique_id=technique_id, technique_name=technique_name,
                                           executors=executors, requirements=requirements, privilege=privilege,
                                           repeatable=repeatable, buckets=buckets, access=access, singleton=singleton,
                                           **ab)

    async def load_executors_from_platform_dict(self, platforms):
        executors = []
        for platform_names, platform_executors in platforms.items():
            for executor_names, executor in platform_executors.items():

                command = executor['command'].strip() if executor.get('command') else None
                cleanup = executor['cleanup'].strip() if executor.get('cleanup') else None

                code = executor['code'].strip() if executor.get('code') else None
                if code:
                    _, code_path = await self.get_service('file_svc').find_file_path(code)
                    if code_path:
                        _, code_data = await self.get_service('file_svc').read_file(code)
                        code = code_data.decode('utf-8').strip()
                    else:
                        code = code

                language = executor.get('language')
                build_target = executor.get('build_target')
                payloads = executor.get('payloads')
                uploads = executor.get('uploads')
                timeout = executor.get('timeout', 60)
                variations = executor.get('variations', [])

                parsers = await self._load_executor_parsers(executor.get('parsers', []))

                for platform_name in platform_names.split(','):
                    for executor_name in executor_names.split(','):
                        executors.append(Executor(name=executor_name, platform=platform_name, command=command,
                                                  code=code, language=language, build_target=build_target,
                                                  payloads=payloads, uploads=uploads, timeout=timeout,
                                                  parsers=parsers, cleanup=cleanup, variations=variations))
        return executors

    async def load_adversary_file(self, filename, access):
        warnings.warn("Function deprecated and will be removed in a future update. Use load_yaml_file", DeprecationWarning)
        await self.load_yaml_file(Adversary, filename, access)

    async def load_source_file(self, filename, access):
        warnings.warn("Function deprecated and will be removed in a future update. Use load_yaml_file", DeprecationWarning)
        await self.load_yaml_file(Source, filename, access)

    async def load_objective_file(self, filename, access):
        warnings.warn("Function deprecated and will be removed in a future update. Use load_yaml_file", DeprecationWarning)
        await self.load_yaml_file(Objective, filename, access)

    async def load_yaml_file(self, object_class, filename, access):
        for src in self.strip_yml(filename):
            obj = object_class.load(src)
            obj.access = access
            await self.store(obj)

    """ PRIVATE """

    async def _load(self, plugins=()):
        try:
            async_tasks = []
            if not plugins:
                plugins = [p for p in await self.locate('plugins') if p.data_dir and p.enabled]
            if not [plugin for plugin in plugins if plugin.data_dir == 'data']:
                plugins.append(Plugin(data_dir='data'))
            for plug in plugins:
                await self._load_payloads(plug)
                await self._load_abilities(plug, async_tasks)
                await self._load_objectives(plug)
                await self._load_adversaries(plug)
                await self._load_planners(plug)
                await self._load_sources(plug)
                await self._load_packers(plug)
            for task in async_tasks:
                await task
            await self._load_extensions()
            await self._load_data_encoders(plugins)
            await self._verify_data_sets()
        except Exception as e:
            self.log.debug(repr(e), exc_info=True)

    async def _load_adversaries(self, plugin):
        for filename in glob.iglob('%s/adversaries/**/*.yml' % plugin.data_dir, recursive=True):
            await self.load_yaml_file(Adversary, filename, plugin.access)

    async def _load_abilities(self, plugin, tasks=None):
        tasks = [] if tasks is None else tasks
        for filename in glob.iglob('%s/abilities/**/*.yml' % plugin.data_dir, recursive=True):
            tasks.append(asyncio.get_event_loop().create_task(self.load_ability_file(filename, plugin.access)))

    @staticmethod
    async def _load_ability_requirements(requirements):
        loaded_reqs = []
        for requirement in requirements:
            for module in requirement:
                loaded_reqs.append(Requirement.load(dict(module=module, relationship_match=requirement[module])))
        return loaded_reqs

    @staticmethod
    async def _load_executor_parsers(parsers):
        ps = []
        for module in parsers:
            ps.append(Parser.load(dict(module=module, parserconfigs=parsers[module])))
        return ps

    async def _load_sources(self, plugin):
        for filename in glob.iglob('%s/sources/*.yml' % plugin.data_dir, recursive=False):
            await self.load_yaml_file(Source, filename, plugin.access)

    async def _load_objectives(self, plugin):
        for filename in glob.iglob('%s/objectives/*.yml' % plugin.data_dir, recursive=False):
            await self.load_yaml_file(Objective, filename, plugin.access)

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
            await self.load_yaml_file(Planner, filename, plugin.access)

    async def _load_extensions(self):
        for entry in self._app_configuration['payloads']['extensions']:
            await self.get_service('file_svc').add_special_payload(entry,
                                                                   self._app_configuration['payloads']
                                                                   ['extensions'][entry])

    async def _load_packers(self, plugin):
        plug_packers = dict()
        for module in glob.iglob('plugins/%s/app/packers/**.py' % plugin.name):
            packer = import_module(module.replace('/', '.').replace('\\', '.').replace('.py', ''))
            if await packer.check_dependencies(self.get_service('app_svc')):
                plug_packers[packer.name] = packer
        self.get_service('file_svc').packers.update(plug_packers)

    async def _load_data_encoders(self, plugins):
        glob_paths = ['app/data_encoders/**.py'] + \
                     ['plugins/%s/app/data_encoders/**.py' % plugin.name for plugin in plugins]
        for glob_path in glob_paths:
            for module_path in glob.iglob(glob_path):
                imported_module = import_module(module_path.replace('/', '.').replace('\\', '.').replace('.py', ''))
                encoder = imported_module.load()
                await self.store(encoder)

    async def _create_ability(self, ability_id, name=None, description=None, tactic=None, technique_id=None,
                              technique_name=None, executors=None, requirements=None, privilege=None,
                              repeatable=False, buckets=None, access=None, singleton=False, **kwargs):
        ability = Ability(ability_id=ability_id, name=name, description=description, tactic=tactic,
                          technique_id=technique_id, technique_name=technique_name, executors=executors,
                          requirements=requirements, privilege=privilege, repeatable=repeatable, buckets=buckets,
                          access=access, singleton=singleton, **kwargs)
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

    async def _verify_data_sets(self):
        await self._verify_abilities()
        await self._verify_default_objective_exists()
        await self._verify_adversary_profiles()

    async def _verify_abilities(self):
        required_fields = ['name', 'description', 'tactic', 'technique_id', 'technique_name']
        special_extensions = [special_payload for special_payload in
                              self.get_service('file_svc').special_payloads if special_payload.startswith('.')]
        cleanup_abilities = await self.locate('abilities', dict(ability_id='4cd4eb44-29a7-4259-91ae-e457b283a880'))
        for ability in await self.locate('abilities'):
            for field in required_fields:
                if not getattr(ability, field):
                    setattr(ability, field, 'auto-generated')
                    self.log.warning('Missing required field in ability %s: %s' % (ability.ability_id, field))
            for executor in ability.executors:
                for payload in executor.payloads:
                    payload_name = payload
                    if self.is_uuid4(payload):
                        payload_name, _ = self.get_service('file_svc').get_payload_name_from_uuid(payload)
                    if (executor.code and payload_name == executor.build_target) or \
                            any(payload_name.endswith(extension) for extension in special_extensions):
                        continue
                    _, path = await self.get_service('file_svc').find_file_path(payload_name)
                    if not path:
                        self.log.warning('Payload referenced in %s but not found: %s', ability.ability_id, payload)
                        continue

                    for cleanup_ability in cleanup_abilities:
                        cleanup_executor = cleanup_ability.find_executor(executor.name, executor.platform)
                        if cleanup_executor and cleanup_executor.cleanup:
                            payload_name = '#{payload:%s}' % payload if self.is_uuid4(payload) else payload
                            cleanup_command = executor.replace_cleanup(cleanup_executor.cleanup[0], payload_name)
                            if cleanup_command not in executor.cleanup:
                                executor.cleanup.append(cleanup_command)

    async def _verify_default_objective_exists(self):
        if not await self.locate('objectives', match=dict(name='default')):
            await self.store(Objective(id='495a9828-cab1-44dd-a0ca-66e58177d8cc', name='default',
                                       description='This is a default objective that runs forever.', goals=[Goal()]))

    async def _verify_adversary_profiles(self):
        for adv in await self.locate('adversaries'):
            if not adv.objective:
                adv.objective = '495a9828-cab1-44dd-a0ca-66e58177d8cc'
            if not next((objective for objective in self.ram['objectives'] if objective.id == adv.objective), None):
                self.log.warning('Objective referenced in %s but not found: %s' % (adv.adversary_id, adv.objective))
            for ability_id in adv.atomic_ordering:
                if not next((ability for ability in self.ram['abilities'] if ability.ability_id == ability_id), None):
                    self.log.warning('Ability referenced in %s but not found: %s' % (adv.adversary_id, ability_id))
            adv.has_repeatable_abilities = adv.check_repeatable_abilities(self.ram['abilities'])
