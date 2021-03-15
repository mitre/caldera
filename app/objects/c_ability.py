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
    tactic = ma.fields.String(missing=None)
    technique_name = ma.fields.String(missing=None)
    technique_id = ma.fields.String(missing=None)
    name = ma.fields.String(missing=None)
    description = ma.fields.String(missing=None)
    cleanup = ma.fields.List(ma.fields.String(), missing=None)
    executor = ma.fields.String(missing=None)
    platform = ma.fields.String(missing=None)
    payloads = ma.fields.List(ma.fields.String(), missing=None)
    uploads = ma.fields.List(ma.fields.String(), missing=None)
    parsers = ma.fields.List(ma.fields.Nested(ParserSchema), missing=None)
    requirements = ma.fields.List(ma.fields.Nested(RequirementSchema), missing=None)
    privilege = ma.fields.String(missing=None)
    timeout = ma.fields.Int(missing=60)
    repeatable = ma.fields.Bool(missing=None)
    language = ma.fields.String(missing=None)
    code = ma.fields.String(missing=None)
    build_target = ma.fields.String(missing=None)
    variations = ma.fields.List(ma.fields.Nested(VariationSchema), missing=None)
    buckets = ma.fields.List(ma.fields.String(), missing=None)
    additional_info = ma.fields.Dict(keys=ma.fields.String(), values=ma.fields.String())
    access = ma.fields.Nested(AccessSchema, missing=None)
    test = ma.fields.String(missing=None)
    singleton = ma.fields.Bool(missing=None)

    @ma.post_load
    def build_ability(self, data, **_):
        if 'technique_name' in data:
            data['technique'] = data.pop('technique_name')
        return Ability(**data)


class Ability(FirstClassObjectInterface, BaseObject):

    schema = AbilitySchema()
    # may need to fix for id=self.unique
    display_schema = AbilitySchema(exclude=['repeatable', 'language', 'code', 'build_target', 'singleton'])

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

    @property
    def raw_command(self):
        return self.decode_bytes(self._test) if self._test else ""

    def __init__(self, ability_id, tactic=None, technique_id=None, technique=None, name=None, test=None,
                 description=None, cleanup=None, executor=None, platform=None, payloads=None, parsers=None,
                 requirements=None, privilege=None, timeout=60, repeatable=False, buckets=None, access=None,
                 variations=None, language=None, code=None, build_target=None, additional_info=None, tags=None,
                 singleton=False, uploads=None, **kwargs):
        super().__init__()
        self._test = test
        self.ability_id = ability_id
        self.tactic = tactic.lower() if tactic else None
        self.technique_name = technique
        self.technique_id = technique_id
        self.name = name
        self.description = description
        self.cleanup = [cleanup] if cleanup else []
        self.executor = executor
        self.platform = platform
        self.payloads = payloads if payloads else []
        self.parsers = parsers if parsers else []
        self.uploads = uploads if uploads else []
        self.requirements = requirements if requirements else []
        self.privilege = privilege
        self.timeout = timeout
        self.repeatable = repeatable
        self.language = language
        self.code = code
        self.build_target = build_target
        self.variations = get_variations(variations)
        self.buckets = buckets if buckets else []
        self.singleton = singleton
        if access:
            self.access = self.Access(access)
        self.additional_info = additional_info or dict()
        self.additional_info.update(**kwargs)
        self.tags = set(tags) if tags else set()

    def __getattr__(self, item):
        try:
            return super().__getattribute__('additional_info')[item]
        except KeyError:
            raise AttributeError(item)

    def store(self, ram):
        existing = self.retrieve(ram['abilities'], self.unique)
        if not existing:
            ram['abilities'].append(self)
            return self.retrieve(ram['abilities'], self.unique)
        existing.update('tactic', self.tactic)
        existing.update('technique_name', self.technique_name)
        existing.update('technique_id', self.technique_id)
        existing.update('name', self.name)
        existing.update('_test', self._test)
        existing.update('description', self.description)
        existing.update('cleanup', self.cleanup)
        existing.update('executor', self.executor)
        existing.update('platform', self.platform)
        existing.update('payloads', self.payloads)
        existing.update('uploads', self.uploads)
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


def get_variations(data):
    variations = []
    if data:
        for v in data:
            if isinstance(v, Variation):
                description = v.description
                command = v.command
            else:
                description = v['description']
                command = v['command']
            variations.append(Variation.load(dict(description=description, command=command)))
    return variations
