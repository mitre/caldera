import re
import os

from app.objects.secondclass.c_parser import Parser
from app.objects.secondclass.c_requirement import Requirement
from app.utility.base_object import BaseObject


class Ability(BaseObject):

    @property
    def test(self):
        decoded_test = self.decode_bytes(self._test)
        for k, v in self.get_config().items():
            if k.startswith('app.'):
                re_variable = re.compile(r'#{(%s.*?)}' % k, flags=re.DOTALL)
                decoded_test = re.sub(re_variable, str(v).strip(), decoded_test)
        return self.encode_string(decoded_test)

    @property
    def unique(self):
        return '%s%s%s' % (self.ability_id, self.platform, self.executor)

    @classmethod
    def from_json(cls, json):
        parsers = [Parser.from_json(p) for p in json['parsers']]
        requirements = [Requirement.from_json(r) for r in json['requirements']]
        return cls(ability_id=json['ability_id'], tactic=json['tactic'], technique_id=json['technique_id'],
                   technique=json['technique_name'], name=json['name'], test=json['test'],
                   description=json['description'], cleanup=json['cleanup'], executor=json['executor'],
                   platform=json['platform'], payload=json['payload'], parsers=parsers,
                   requirements=requirements, privilege=json['privilege'], timeout=json['timeout'], access=json['access'])

    @property
    def display(self):
        return self.clean(dict(id=self.unique, ability_id=self.ability_id, tactic=self.tactic,
                               technique_name=self.technique_name,
                               technique_id=self.technique_id, name=self.name,
                               test=self.test, description=self.description, cleanup=self.cleanup,
                               executor=self.executor, unique=self.unique,
                               platform=self.platform, payload=self.payload, parsers=[p.display for p in self.parsers],
                               requirements=[r.display for r in self.requirements], privilege=self.privilege,
                               timeout=self.timeout, access=self.access.value))

    def __init__(self, ability_id, tactic=None, technique_id=None, technique=None, name=None, test=None,
                 description=None, cleanup=None, executor=None, platform=None, payload=None, parsers=None,
                 requirements=None, privilege=None, timeout=60, repeatable=False, access=None):
        super().__init__()
        self._test = test
        self.ability_id = ability_id
        self.tactic = tactic
        self.technique_name = technique
        self.technique_id = technique_id
        self.name = name
        self.description = description
        self.cleanup = cleanup
        self.executor = executor
        self.platform = platform
        self.payload = payload
        self.parsers = parsers
        self.requirements = requirements
        self.privilege = privilege
        self.timeout = timeout
        self.repeatable = repeatable
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
        existing.update('payload', self.payload)
        existing.update('privilege', self.privilege)
        existing.update('timeout', self.timeout)
        return existing

    async def which_plugin(self):
        for plugin in os.listdir('plugins'):
            if await self.walk_file_path(os.path.join('plugins', plugin, 'data', ''), '%s.yml' % self.ability_id):
                return plugin
        return None
