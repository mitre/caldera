import collections
import logging
import uuid

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_executor import ExecutorSchema
from app.objects.secondclass.c_requirement import RequirementSchema
from app.utility.base_object import BaseObject
from app.utility.base_world import AccessSchema

from neo4j import GraphDatabase

class AbilitySchema(ma.Schema):
    ability_id = ma.fields.String()
    tactic = ma.fields.String(missing=None)
    technique_name = ma.fields.String(missing=None)
    technique_id = ma.fields.String(missing=None)
    name = ma.fields.String(missing=None)
    description = ma.fields.String(missing=None)
    executors = ma.fields.List(ma.fields.Nested(ExecutorSchema))
    requirements = ma.fields.List(ma.fields.Nested(RequirementSchema), missing=None)
    privilege = ma.fields.String(missing=None)
    repeatable = ma.fields.Bool(missing=None)
    buckets = ma.fields.List(ma.fields.String(), missing=None)
    additional_info = ma.fields.Dict(keys=ma.fields.String(), values=ma.fields.String())
    access = ma.fields.Nested(AccessSchema, missing=None)
    singleton = ma.fields.Bool(missing=None)
    plugin = ma.fields.String(missing=None)
    delete_payload = ma.fields.Bool(missing=None)

    @ma.pre_load
    def fix_id(self, data, **_):
        if 'id' in data:
            data['ability_id'] = data.pop('id')
        return data

    @ma.post_load
    def build_ability(self, data, **kwargs):
        if 'technique' in data:
            data['technique_name'] = data.pop('technique')
        return None if kwargs.get('partial') is True else Ability(**data)


class Ability(FirstClassObjectInterface, BaseObject):

    schema = AbilitySchema()
    display_schema = AbilitySchema()

    HOOKS = dict()

    @property
    def unique(self):
        return self.ability_id

    @property
    def executors(self):
        yield from self._executor_map.values()

    def __init__(self, ability_id='', name=None, description=None, tactic=None, technique_id=None, technique_name=None,
                 executors=(), requirements=None, privilege=None, repeatable=False, buckets=None, access=None,
                 additional_info=None, tags=None, singleton=False, plugin='', delete_payload=True, **kwargs):
        super().__init__()
        self.ability_id = ability_id if ability_id else str(uuid.uuid4())
        self.tactic = tactic.lower() if tactic else None
        self.technique_name = technique_name
        self.technique_id = technique_id
        self.name = name
        self.description = description

        self._executor_map = collections.OrderedDict()
        self.add_executors(executors)

        self.requirements = requirements if requirements else []
        self.privilege = privilege
        self.repeatable = repeatable
        self.buckets = buckets if buckets else []
        self.singleton = singleton
        if access:
            self.access = self.Access(access)
        self.additional_info = additional_info or dict()
        self.additional_info.update(**kwargs)
        self.tags = set(tags) if tags else set()
        self.plugin = plugin
        self.delete_payload = delete_payload

        # Connect to Neo4j Database
        neo4j_uri = "bolt://localhost:7687"
        neo4j_user = "neo4j"
        neo4j_password = "calderaadmin"
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def __getattr__(self, item):
        try:
            return super().__getattribute__('additional_info')[item]
        except KeyError:
            raise AttributeError(item)

    # def store(self, ram):
    #     existing = self.retrieve(ram['abilities'], self.unique)
    #     if not existing:
    #         name_match = [x for x in ram['abilities'] if x.name == self.name]
    #         if name_match:
    #             self.name = self.name + " (2)"
    #             logging.debug(f"Collision in ability name detected for {self.ability_id} and {name_match[0].ability_id} "
    #                           f"({name_match[0].name}). Modifying name of the second ability to {self.name}...")
    #         ram['abilities'].append(self)
    #         return self.retrieve(ram['abilities'], self.unique)
    #     existing.update('tactic', self.tactic)
    #     existing.update('technique_name', self.technique_name)
    #     existing.update('technique_id', self.technique_id)
    #     existing.update('name', self.name)
    #     existing.update('description', self.description)
    #     existing.update('_executor_map', self._executor_map)
    #     existing.update('privilege', self.privilege)
    #     existing.update('repeatable', self.repeatable)
    #     existing.update('buckets', self.buckets)
    #     existing.update('tags', self.tags)
    #     existing.update('singleton', self.singleton)
    #     existing.update('plugin', self.plugin)
    #     existing.update('delete_payload', self.delete_payload)
    #     return existing

# The following is a test function to see if I can get the neo4j database to work
    async def store(self):
        print(" ")
        print("c_ability.py: Ability.store()")
        print(self.unique)
        print(self.name)
        async def retrieve(session, label, unique):
            query = f"MATCH (n:{label} {{unique: $unique}}) RETURN n"
            result = await session.run(query, unique=unique)
            record = result.single()
            if record:
                return record['n']
            return None
        try:
            session = self.driver.session()
            existing = await retrieve(session, 'abilities', self.unique)
            if not existing:
                name_match = await session.run(
                    "MATCH (a:Ability) WHERE a.name = $name RETURN a",
                    name=self.name
                )
                if name_match.single() is not None:
                    self.name = self.name + " (2)"
                    logging.debug(f"Collision in ability name detected. Modifying name to {self.name}...")
                await session.run(
                    "CREATE (a:Ability {tactic: $tactic, technique_name: $technique_name, technique_id: $technique_id, "
                    "name: $name, description: $description, _executor_map: $executor_map, privilege: $privilege, "
                    "repeatable: $repeatable, buckets: $buckets, tags: $tags, singleton: $singleton, "
                    "plugin: $plugin, delete_payload: $delete_payload})",
                    tactic=self.tactic,
                    technique_name=self.technique_name,
                    technique_id=self.technique_id,
                    name=self.name,
                    description=self.description,
                    executor_map=self._executor_map,
                    privilege=self.privilege,
                    repeatable=self.repeatable,
                    buckets=self.buckets,
                    tags=self.tags,
                    singleton=self.singleton,
                    plugin=self.plugin,
                    delete_payload=self.delete_payload
                )
            else:
                await session.run(
                    "MATCH (a:Ability) WHERE ID(a) = $id SET "
                    "a.tactic = $tactic, a.technique_name = $technique_name, a.technique_id = $technique_id, "
                    "a.name = $name, a.description = $description, a._executor_map = $executor_map, "
                    "a.privilege = $privilege, a.repeatable = $repeatable, a.buckets = $buckets, a.tags = $tags, "
                    "a.singleton = $singleton, a.plugin = $plugin, a.delete_payload = $delete_payload",
                    id=existing['id'],
                    tactic=self.tactic,
                    technique_name=self.technique_name,
                    technique_id=self.technique_id,
                    name=self.name,
                    description=self.description,
                    executor_map=self._executor_map,
                    privilege=self.privilege,
                    repeatable=self.repeatable,
                    buckets=self.buckets,
                    tags=self.tags,
                    singleton=self.singleton,
                    plugin=self.plugin,
                    delete_payload=self.delete_payload
                )
            return self
        except Exception as e:
            self.log.error('[!] Error storing object: %s' % e)
        finally:
            # Perform any necessary cleanup or closing operations
            print("Closing Neo4j session")
            if session is not None:
                session.close()
# End of test function

    async def which_plugin(self):
        return self.plugin

    def find_executor(self, name, platform):
        return self._executor_map.get(self._make_executor_map_key(name, platform))

    def find_executors(self, names, platform):
        """Find executors for matching platform/executor names

        Only the first instance of a matching executor will be returned,
            as there should not be multiple executors matching a single
            platform/executor name pair.

        :param names: Executors to search. ex: ['psh', 'cmd']
        :type names: list(str)
        :param platform: Platform to search. ex: windows
        :type platform: str
        :return: List of executors ordered based on ordering of `names`
        :rtype: list(Executor)
        """
        executors = []
        seen_names = set()
        for name in names:
            if name in seen_names:
                continue
            seen_names.add(name)

            executor = self.find_executor(name, platform)
            if executor:
                executors.append(executor)

        return executors

    def add_executor(self, executor):
        """Add executor to map

        If the executor exists, delete the current entry and add the
            new executor to the bottom for FIFO
        """
        map_key = self._make_executor_map_key(executor.name, executor.platform)
        if map_key in self._executor_map:
            del self._executor_map[map_key]
        self._executor_map[map_key] = executor

    def add_executors(self, executors):
        """Create executor map from list of executor objects"""
        for executor in executors:
            self.add_executor(executor)

    def remove_all_executors(self):
        self._executor_map = collections.OrderedDict()

    async def add_bucket(self, bucket):
        if bucket not in self.buckets:
            self.buckets.append(bucket)

    @staticmethod
    def _make_executor_map_key(name, platform):
        return name, platform
