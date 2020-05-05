import os
from base64 import b64decode

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_parser import Parser
from app.objects.secondclass.c_requirement import Requirement
from app.objects.secondclass.c_variation import Variation
from app.utility.base_object import BaseObject


class Ability(FirstClassObjectInterface, BaseObject):

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

    @classmethod
    def from_json(cls, json):
        parsers = [Parser.from_json(p) for p in json['parsers']]
        requirements = [Requirement.from_json(r) for r in json['requirements']]
        return cls(ability_id=json['ability_id'], tactic=json['tactic'], technique_id=json['technique_id'],
                   technique=json['technique_name'], name=json['name'], test=json['test'], variations=[],
                   description=json['description'], cleanup=json['cleanup'], executor=json['executor'],
                   platform=json['platform'], payloads=json['payloads'], parsers=parsers,
                   requirements=requirements, privilege=json['privilege'], buckets=json['buckets'],
                   timeout=json['timeout'], access=json['access'])

    @property
    def display(self):
        return self.clean(dict(id=self.unique, ability_id=self.ability_id, tactic=self.tactic,
                               technique_name=self.technique_name,
                               technique_id=self.technique_id, name=self.name,
                               test=self.test, description=self.description, cleanup=self.cleanup,
                               executor=self.executor, unique=self.unique,
                               platform=self.platform, payloads=self.payloads, parsers=[p.display for p in self.parsers],
                               requirements=[r.display for r in self.requirements], privilege=self.privilege,
                               timeout=self.timeout, buckets=self.buckets, access=self.access.value, variations=[v.display for v in self.variations]))

    def __init__(self, ability_id, tactic=None, technique_id=None, technique=None, name=None, test=None,
                 description=None, cleanup=None, executor=None, platform=None, payloads=None, parsers=None,
                 requirements=None, privilege=None, timeout=60, repeatable=False, buckets=None, access=None,
                 variations=None, language=None, code=None, build_target=None):
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
