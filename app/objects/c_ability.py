import os
from base64 import b64decode

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_parser import ParserSchema
from app.objects.secondclass.c_requirement import RequirementSchema
from app.objects.secondclass.c_variation import Variation, VariationSchema
from app.utility.base_object import BaseObject
from app.utility.base_world import AccessSchema


class AbilitySchema(ma.Schema):
    ability_id = ma.fields.String()
    tactic = ma.fields.String()
    technique_name = ma.fields.String()
    technique_id = ma.fields.String()
    name = ma.fields.String()
    description = ma.fields.String()
    cleanup = ma.fields.List(ma.fields.String())
    executor = ma.fields.String()
    platform = ma.fields.String()
    payloads = ma.fields.List(ma.fields.String())
    parsers = ma.fields.List(ma.fields.Nested(ParserSchema))
    requirements = ma.fields.List(ma.fields.Nested(RequirementSchema))
    privilege = ma.fields.String()
    timeout = ma.fields.Int()
    repeatable = ma.fields.Bool()
    language = ma.fields.String()
    code = ma.fields.String()
    build_target = ma.fields.String()
    variations = ma.fields.List(ma.fields.Nested(VariationSchema))
    buckets = ma.fields.List(ma.fields.String())
    additional_info = ma.fields.Dict(keys=ma.fields.String(), values=ma.fields.String())
    access = ma.fields.Nested(AccessSchema)
    test = ma.fields.String()

    @ma.post_load
    def build_ability(self, data, **_):
        return Ability(**data)


class Ability(FirstClassObjectInterface, BaseObject):

    schema = AbilitySchema()
    display_schema = AbilitySchema(exclude=['repeatable', 'language', 'code', 'build_target'])  # may need to fix for id=self.unique

    RESERVED = dict(payload='#{payload}')
    HOOKS = dict()

    @property
    def test(self):
        return self.replace_app_props(self._test)

    @test.setter
    def test(self, cmd):
        self._test = self.encode_string(cmd)

    @property
    def unique(self):
        return '%s%s%s' % (self.ability_id, self.platform, self.executor)

    def __init__(self, ability_id, tactic=None, technique_id=None, technique=None, name=None, test=None,
                 description=None, cleanup=None, executor=None, platform=None, payloads=None, parsers=None,
                 requirements=None, privilege=None, timeout=60, repeatable=False, buckets=None, access=None,
                 variations=None, language=None, code=None, build_target=None, **kwargs):
        super().__init__()
        self._test = test
        self.ability_id = ability_id
        self.tactic = tactic
        self.technique_name = technique
        self.technique_id = technique_id
        self.name = name
        self.description = description
        self.cleanup = [cleanup] if cleanup else []
        self.executor = executor
        self.platform = platform
        self.payloads = payloads if payloads else []
        self.parsers = parsers if parsers else []
        self.requirements = requirements if requirements else []
        self.privilege = privilege
        self.timeout = timeout
        self.repeatable = repeatable
        self.language = language
        self.code = code
        self.build_target = build_target
        self.variations = [Variation.load(dict(description=v['description'], command=v['command'])) for v in variations] if variations else []
        self.buckets = buckets
        if access:
            self.access = self.Access(access)
        self.additional_info = dict()
        for k, v in kwargs.items():
            self.additional_info[k] = v

    def store(self, ram):
        existing = self.retrieve(ram['abilities'], self.unique)
        if not existing:
            ram['abilities'].append(self)
            return self.retrieve(ram['abilities'], self.unique)
        existing.update('tactic', self.tactic)
        existing.update('technique_name', self.technique_name)
        existing.update('technique_id', self.technique_id)
        existing.update('name', self.name)
        existing.update('_test', self.test)
        existing.update('description', self.description)
        existing.update('cleanup', self.cleanup)
        existing.update('executor', self.executor)
        existing.update('platform', self.platform)
        existing.update('payloads', self.payloads)
        existing.update('privilege', self.privilege)
        existing.update('timeout', self.timeout)
        existing.update('code', self.code)
        existing.update('language', self.language)
        existing.update('build_target', self.build_target)
        return existing

    async def which_plugin(self):
        for plugin in os.listdir('plugins'):
            if await self.walk_file_path(os.path.join('plugins', plugin, 'data', ''), '%s.yml' % self.ability_id):
                return plugin
        return None

    def replace_cleanup(self, encoded_cmd, payload):
        decoded_cmd = b64decode(encoded_cmd).decode('utf-8', errors='ignore').replace('\n', '')
        decoded_cmd = decoded_cmd.replace(self.RESERVED['payload'], payload)
        return decoded_cmd

    async def add_bucket(self, bucket):
        if bucket not in self.buckets:
            self.buckets.append(bucket)
