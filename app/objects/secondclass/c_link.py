import logging
from base64 import b64decode
from datetime import datetime
from importlib import import_module

from app.objects.c_ability import Ability
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_visibility import Visibility
from app.utility.base_object import BaseObject


class Link(BaseObject):

    @classmethod
    def from_json(cls, json):
        ability = Ability.from_json(json['ability'])
        return cls(id=json['id'], pin=json['pin'], operation=json['operation'], command=json['command'],
                   paw=json['paw'], host=json['host'], ability=ability)

    @property
    def unique(self):
        return self.hash('%s-%s' % (self.operation, self.id))

    @property
    def display(self):
        return self.clean(dict(id=self.id, operation=self.operation, paw=self.paw, command=self.command,
                               executor=self.ability.executor, status=self.status, score=self.score,
                               decide=self.decide.strftime('%Y-%m-%d %H:%M:%S'), pin=self.pin,
                               facts=[fact.display for fact in self.facts], unique=self.unique,
                               collect=self.collect.strftime('%Y-%m-%d %H:%M:%S') if self.collect else '',
                               finish=self.finish, ability=self.ability.display, cleanup=self.cleanup,
                               visibility=self.visibility.display, host=self.host, output=self.output))

    @property
    def pin(self):
        return self._pin

    @pin.setter
    def pin(self, p):
        self._pin = p

    @property
    def states(self):
        return dict(HIGH_VIZ=-5,
                    UNTRUSTED=-4,
                    EXECUTE=-3,
                    DISCARD=-2,
                    PAUSE=-1)

    def __init__(self, operation, command, paw, ability, status=-3, score=0, jitter=0, cleanup=0, id=None, pin=0, host=None):
        super().__init__()
        self.id = id
        self.command = command
        self.operation = operation
        self.paw = paw
        self.host = host
        self.cleanup = cleanup
        self.ability = ability
        self.status = status
        self.score = score
        self.jitter = jitter
        self.decide = datetime.now()
        self.pid = None
        self.collect = None
        self.finish = None
        self.facts = []
        self.relationships = []
        self.used = []
        self.visibility = Visibility()
        self._pin = pin
        self.output = False

    async def parse(self, operation, result):
        try:
            if self.status != 0:
                return
            for parser in self.ability.parsers:
                relationships = await self._parse_link_result(result, parser, operation.source)
                await self._update_scores(operation, increment=len(relationships))
                await self._create_relationships(relationships, operation)
        except Exception as e:
            logging.getLogger('link').debug('parse exception: %s' % e)

    def apply_id(self, host):
        self.id = self.generate_number()
        self.host = host

    def can_ignore(self):
        return self.status in [self.states['DISCARD'], self.states['HIGH_VIZ']]

    """ PRIVATE """

    async def _parse_link_result(self, result, parser, source):
        blob = b64decode(result).decode('utf-8')
        parser_info = dict(module=parser.module, used_facts=self.used, mappers=parser.parserconfigs, source=source)
        p_inst = await self._load_module('Parser', parser_info)
        try:
            return p_inst.parse(blob=blob)
        except Exception:
            return []

    @staticmethod
    async def _load_module(module_type, module_info):
        module = import_module(module_info['module'])
        return getattr(module, module_type)(module_info)

    async def _create_relationships(self, relationships, operation):
        for relationship in relationships:
            await self._save_fact(operation, relationship.source, relationship.score)
            await self._save_fact(operation, relationship.target, relationship.score)
            self.relationships.append(relationship)

    async def _save_fact(self, operation, trait, score):
        if all(trait) and not any(f.trait == trait[0] and f.value == trait[1] for f in operation.all_facts()):
            self.facts.append(Fact(trait=trait[0], value=trait[1], score=score, collected_by=self.paw,
                                   technique_id=self.ability.technique_id))

    async def _update_scores(self, operation, increment):
        for uf in self.used:
            for found_fact in operation.all_facts():
                if found_fact.unique == uf.unique:
                    found_fact.score += increment
                    break
