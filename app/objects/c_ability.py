import collections
import logging
import uuid

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_executor import ExecutorSchema
from app.objects.secondclass.c_requirement import RequirementSchema
from app.utility.base_object import BaseObject
from app.utility.base_world import AccessSchema


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

    def __getattr__(self, item):
        try:
            return super().__getattribute__('additional_info')[item]
        except KeyError:
            raise AttributeError(item)

    def store(self, ram):
        existing = self.retrieve(ram['abilities'], self.unique)
        if not existing:
            name_match = [x for x in ram['abilities'] if x.name == self.name]
            if name_match:
                self.name = self.name + " (2)"
                logging.debug(f"Collision in ability name detected for {self.ability_id} and {name_match[0].ability_id} "
                              f"({name_match[0].name}). Modifying name of the second ability to {self.name}...")
            ram['abilities'].append(self)
            return self.retrieve(ram['abilities'], self.unique)
        existing.update('tactic', self.tactic)
        existing.update('technique_name', self.technique_name)
        existing.update('technique_id', self.technique_id)
        existing.update('name', self.name)
        existing.update('description', self.description)
        existing.update('_executor_map', self._executor_map)
        existing.update('privilege', self.privilege)
        existing.update('repeatable', self.repeatable)
        existing.update('buckets', self.buckets)
        existing.update('tags', self.tags)
        existing.update('singleton', self.singleton)
        existing.update('plugin', self.plugin)
        existing.update('delete_payload', self.delete_payload)
        return existing

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
