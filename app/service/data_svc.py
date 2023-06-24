import asyncio
import copy
import datetime
import glob
import os
import pickle
import tarfile
import shutil
import warnings
import pathlib
from importlib import import_module

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_objective import Objective
from app.objects.c_planner import Planner
from app.objects.c_plugin import Plugin
from app.objects.c_source import Source
from app.objects.secondclass.c_executor import Executor, ExecutorSchema
from app.objects.secondclass.c_goal import Goal
from app.objects.secondclass.c_parser import Parser
from app.objects.secondclass.c_requirement import Requirement, RequirementSchema
from app.service.interfaces.i_data_svc import DataServiceInterface
from app.utility.base_service import BaseService

from neo4j import GraphDatabase

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

PAYLOADS_CONFIG_STANDARD_KEY = 'standard_payloads'
PAYLOADS_CONFIG_SPECIAL_KEY = 'special_payloads'
PAYLOADS_CONFIG_EXTENSIONS_KEY = 'extensions'

DEPRECATION_WARNING_LOAD = "Function deprecated and will be removed in a future update. Use load_yaml_file"


class DataService(DataServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('data_svc', self)
        # self.schema = dict(agents=[], planners=[], adversaries=[], abilities=[], sources=[], operations=[],
        #                    schedules=[], plugins=[], obfuscators=[], objectives=[], data_encoders=[])
        # self.ram = copy.deepcopy(self.schema)
        # Connect to Neo4j Database
        neo4j_uri = "bolt://localhost:7687"
        neo4j_user = "neo4j"
        neo4j_password = "calderaadmin"
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    async def store(self, c_object):
        """
        Store the object in Neo4j database.
        Assumes c_object has properties like unique, trait, name, value, etc.
        """

        # The query to create a fact node in Neo4j
        query = """
        CREATE (f:Fact {
            unique: $unique,
            trait: $trait,
            name: $name,
            value: $value,
            created: $created,
            score: $score,
            source: $source,
            origin_type: $origin_type,
            links: $links,
            relationships: $relationships,
            limit_count: $limit_count,
            collected_by: $collected_by,
            technique_id: $technique_id
        })
        """

        # Parameters to be passed to the query
        params = {
            'unique': getattr(c_object, 'unique', None),
            'trait': getattr(c_object, 'trait', None),
            'name': getattr(c_object, 'name', None),
            'value': getattr(c_object, 'value', None),
            'created': getattr(c_object, 'created', None),
            'score': getattr(c_object, 'score', None),
            'source': getattr(c_object, 'source', None),
            'origin_type': getattr(c_object, 'origin_type', None),
            'links': getattr(c_object, 'links', []),
            'relationships': getattr(c_object, 'relationships', []),
            'limit_count': getattr(c_object, 'limit_count', None),
            'collected_by': getattr(c_object, 'collected_by', []),
            'technique_id': getattr(c_object, 'technique_id', None)
        }

        # Execute the query
        with self.driver.session() as session:
            session.run(query, params)

    @staticmethod
    def _iter_data_files(self):
        """Yield paths to data files managed by caldera.

        The files paths are relative to the root caldera folder, so they
        will begin with "data/".

        Note:
            This will skip any files starting with '.' (e.g., '.gitkeep').
        """
        for data_glob in DATA_FILE_GLOBS:
            for f in glob.glob(data_glob):
                yield f

        with self.driver.session() as session:
            # Create empty abilities node
            session.run("CREATE (:Abilities)")

            # Create empty adversaries node
            session.run("CREATE (:Adversaries)")

            # Create empty facts node
            session.run("CREATE (:Facts)")

            # Create empty objectives node
            session.run("CREATE (:Objectives)")

            # Create empty payloads node
            session.run("CREATE (:Payloads)")

            # Create empty results node
            session.run("CREATE (:Results)")

            # Create empty sources node
            session.run("CREATE (:Sources)")

            # Create empty object_store node
            session.run("CREATE (:ObjectStore)")

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

    # async def restore_state(self):
        # """
        # Restore the object database

        # :return:
        # """
        # if os.path.exists('data/object_store'):
        #     _, store = await self.get_service('file_svc').read_file('object_store', 'data')
        #     # Pickle is only used to load a local file that caldera creates. Pickled data is not
        #     # received over the network.
        #     ram = pickle.loads(store)  # nosec
        #     for key in ram.keys():
        #         self.ram[key] = []
        #         for c_object in ram[key]:
        #             await self.store(c_object)
        #     self.log.debug('Restored data from persistent storage')
        # self.log.debug('There are %s jobs in the scheduler' % len(self.ram['schedules']))

    async def restore_state(self, profile_id=None):
        """
        Restore the object database from the Neo4j database for a particular profile

        :param profile_id: The unique identifier of the profile to restore
        :return:
        """
        try:
            with self.driver.session() as session:

                # Query to check if the profile with a specific id exists in Neo4j.
                # Modify this query according to your data model in Neo4j
                query = "MATCH (p:Profile) WHERE p.id = $profile_id RETURN p"

                # Running the query
                result = session.run(query, profile_id=profile_id)

                # Check if profile exists
                profile = result.single()
                if profile is None:
                    self.log.debug(f'No profile found with id {profile_id}')
                    return
                
                # If profile exists, restore the state (continue with your logic)
                # ...

                # Log success message
                self.log.debug(f'Restored data for profile {profile_id} from Neo4j database')

        except Exception as e:
            self.log.error(f'[!] RESTORE_STATE: {e}')


    async def apply(self, collection):
        if collection not in self.ram:
            self.ram[collection] = []

    async def load_data(self, plugins=()):
        loop = asyncio.get_event_loop()
        loop.create_task(self._load(plugins))

    async def reload_data(self, plugins=()):
        await self._load(plugins)

    # async def store(self, c_object):
    #     try:
    #         return c_object.store(self.ram)
    #     except Exception as e:
    #         self.log.error('[!] can only store first-class objects: %s' % e)

    # async def locate(self, object_name, match=None):
    #     try:
    #         return [obj for obj in self.ram[object_name] if obj.match(match)]
    #     except Exception as e:
    #         self.log.error('[!] LOCATE: %s' % e)

    async def locate(self, object_name, match=None):
        print("object_name: %s"%object_name)
        print("object type: %s"%type(object_name))
        
        try:
            with self.driver.session() as session:
                # Check if the node type exists
                exists = session.run(f"MATCH (n:{object_name}) RETURN count(n)>0 as exists").single()['exists']
                if not exists:
                    return []

                # Write the Cypher query to locate the object
                query = f"MATCH (n:{object_name}) WHERE n.name = $name RETURN n"
                
                # Execute the query
                results = session.run(query, name=match)
                
                # Process the results
                objects = [record['n'] for record in results]
                return objects
        except Exception as e:
            self.log.error(f'[!] LOCATE: {e}')



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
                executors = await self.convert_v0_ability_executor(ab)
                technique_id = self.convert_v0_ability_technique_id(ab)
                technique_name = self.convert_v0_ability_technique_name(ab)
                privilege = ab.pop('privilege', None)
                repeatable = ab.pop('repeatable', False)
                singleton = ab.pop('singleton', False)
                requirements = await self.convert_v0_ability_requirements(ab.pop('requirements', []))
                buckets = ab.pop('buckets', [tactic])
                ab.pop('access', None)
                plugin = self._get_plugin_name(filename)
                ab.pop('plugin', plugin)

                if tactic and tactic not in filename:
                    self.log.error('Ability=%s has wrong tactic' % ability_id)

                await self._create_ability(ability_id=ability_id, name=name, description=description, tactic=tactic,
                                           technique_id=technique_id, technique_name=technique_name,
                                           executors=executors, requirements=requirements, privilege=privilege,
                                           repeatable=repeatable, buckets=buckets, access=access, singleton=singleton, plugin=plugin,
                                           **ab)

    async def convert_v0_ability_executor(self, ability_data: dict):
        """Checks if ability file follows v0 executor format, otherwise assumes v1 ability formatting."""
        if 'platforms' in ability_data:
            return await self.load_executors_from_platform_dict(ability_data.pop('platforms', dict()))
        return await self.load_executors_from_list(ability_data.pop('executors', []))

    def convert_v0_ability_technique_name(self, ability_data: dict):
        """Checks if ability file follows v0 technique_name format, otherwise assumes v1 ability formatting."""
        if 'technique' in ability_data:
            return ability_data.pop('technique', dict()).get('name')
        return ability_data.pop('technique_name')

    def convert_v0_ability_technique_id(self, ability_data: dict):
        """Checks if ability file follows v0 technique_id format, otherwise assumes v1 ability formatting."""
        if 'technique' in ability_data:
            return ability_data.get('technique', dict()).get('attack_id')
        return ability_data.pop('technique_id')

    async def convert_v0_ability_requirements(self, requirements_data: list):
        """Checks if ability file follows v0 requirement format, otherwise assumes v1 ability formatting."""
        if requirements_data and 'relationship_match' not in requirements_data[0]:
            return await self._load_ability_requirements(requirements_data)
        return await self.load_requirements_from_list(requirements_data)

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

    async def load_executors_from_list(self, executors: list):
        return [ExecutorSchema().load(entry) for entry in executors]

    async def load_requirements_from_list(self, requirements: list):
        return [RequirementSchema().load(entry) for entry in requirements]

    async def load_adversary_file(self, filename, access):
        warnings.warn(DEPRECATION_WARNING_LOAD, DeprecationWarning, stacklevel=2)
        await self.load_yaml_file(Adversary, filename, access)

    async def load_source_file(self, filename, access):
        warnings.warn(DEPRECATION_WARNING_LOAD, DeprecationWarning, stacklevel=2)
        await self.load_yaml_file(Source, filename, access)

    async def load_objective_file(self, filename, access):
        warnings.warn(DEPRECATION_WARNING_LOAD, DeprecationWarning, stacklevel=2)
        await self.load_yaml_file(Objective, filename, access)

    async def load_yaml_file(self, object_class, filename, access):
        for src in self.strip_yml(filename):
            obj = object_class.load(src)
            obj.access = access
            obj.plugin = self._get_plugin_name(filename)
            await self.store(obj)

    async def create_or_update_everything_adversary(self):
        everything = {
            'id': '785baa02-df5d-450a-ab3a-1a863f22b4b0',
            'name': 'Everything Bagel',
            'description': 'An adversary with all adversary abilities',
            'atomic_ordering': [
                ability.ability_id
                for ability in await self.locate('abilities')
                if (
                    ability.access == self.Access.RED
                    or ability.access == self.Access.APP
                )
                and ability.plugin != 'training'
            ],
        }
        obj = Adversary.load(everything)
        obj.access = self.Access.RED
        await self.store(obj)

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
            await self.create_or_update_everything_adversary()
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
        payload_config = dict(
            standard_payloads=dict(),
            special_payloads=dict(),
            extensions=dict(),
        )
        for filename in glob.iglob('%s/payloads/*.yml' % plugin.data_dir, recursive=False):
            data = self.strip_yml(filename)
            special_payloads = data[0].get(PAYLOADS_CONFIG_SPECIAL_KEY, dict())
            extensions = data[0].get(PAYLOADS_CONFIG_EXTENSIONS_KEY, dict())
            standard_payloads = data[0].get(PAYLOADS_CONFIG_STANDARD_KEY, dict())
            payload_config[PAYLOADS_CONFIG_STANDARD_KEY].update(standard_payloads)
            if special_payloads:
                await self._apply_special_payload_hooks(special_payloads)
                payload_config[PAYLOADS_CONFIG_SPECIAL_KEY].update(special_payloads)
            if extensions:
                await self._apply_special_extension_hooks(extensions)
                payload_config[PAYLOADS_CONFIG_EXTENSIONS_KEY].update(extensions)
        self._update_payload_config(payload_config, plugin.name)

    def _update_payload_config(self, updates, curr_plugin_name):
        payload_config = self.get_config(name='payloads')
        curr_standard_payloads = payload_config.get(PAYLOADS_CONFIG_STANDARD_KEY, dict())
        curr_special_payloads = payload_config.get(PAYLOADS_CONFIG_SPECIAL_KEY, dict())
        curr_extensions = payload_config.get(PAYLOADS_CONFIG_EXTENSIONS_KEY, dict())
        new_standard_payloads = updates.get(PAYLOADS_CONFIG_STANDARD_KEY, dict())
        new_special_payloads = updates.get(PAYLOADS_CONFIG_SPECIAL_KEY, dict())
        new_extensions = updates.get(PAYLOADS_CONFIG_EXTENSIONS_KEY, dict())

        self._check_payload_overlaps(curr_standard_payloads, new_standard_payloads, PAYLOADS_CONFIG_STANDARD_KEY,
                                     curr_plugin_name)
        self._check_payload_overlaps(curr_special_payloads, new_special_payloads, PAYLOADS_CONFIG_SPECIAL_KEY,
                                     curr_plugin_name)
        self._check_payload_overlaps(curr_extensions, new_extensions, PAYLOADS_CONFIG_EXTENSIONS_KEY, curr_plugin_name)

        payload_config[PAYLOADS_CONFIG_STANDARD_KEY] = {**curr_standard_payloads, **new_standard_payloads}
        payload_config[PAYLOADS_CONFIG_SPECIAL_KEY] = {**curr_special_payloads, **new_special_payloads}
        payload_config[PAYLOADS_CONFIG_EXTENSIONS_KEY] = {**curr_extensions, **new_extensions}
        self.apply_config(name='payloads', config=payload_config)

    def _check_payload_overlaps(self, old_dict, new_dict, config_section_name, curr_plugin_name):
        overlap = set(old_dict).intersection(new_dict)
        for payload in overlap:
            if old_dict[payload] != new_dict[payload]:
                self.log.warning('Config for %s already exists in the %s section of the payloads config and will be '
                                 'overridden using new payload config data from plugin %s', payload,
                                 config_section_name, curr_plugin_name)

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
                              repeatable=False, buckets=None, access=None, singleton=False, plugin='', **kwargs):
        ability = Ability(ability_id=ability_id, name=name, description=description, tactic=tactic,
                          technique_id=technique_id, technique_name=technique_name, executors=executors,
                          requirements=requirements, privilege=privilege, repeatable=repeatable, buckets=buckets,
                          access=access, singleton=singleton, plugin=plugin, **kwargs)
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

    async def _verify_default_objective_exists(self):
        if not await self.locate('objectives', match=dict(name='default')):
            await self.store(Objective(id='495a9828-cab1-44dd-a0ca-66e58177d8cc', name='default',
                                       description='This is a default objective that runs forever.', goals=[Goal()]))

    async def _verify_adversary_profiles(self):
        for adv in await self.locate('adversaries'):
            adv.verify(log=self.log, abilities=self.ram['abilities'], objectives=self.ram['objectives'])

    def _get_plugin_name(self, filename):
        plugin_path = pathlib.PurePath(filename).parts
        return plugin_path[1] if 'plugins' in plugin_path else ''
