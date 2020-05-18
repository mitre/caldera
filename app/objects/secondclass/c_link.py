import logging
from base64 import b64decode
from datetime import datetime
from importlib import import_module

import marshmallow as ma

from app.objects.c_ability import Ability
from app.objects.secondclass.c_fact import Fact, FactSchema
from app.objects.secondclass.c_visibility import Visibility, VisibilitySchema
from app.utility.base_object import BaseObject


class LinkSchema(ma.Schema):

    class Meta:
        unknown = ma.EXCLUDE

    id = ma.fields.Integer(missing=None)
    paw = ma.fields.String()
    command = ma.fields.String()
    status = ma.fields.Integer(missing=-3)
    score = ma.fields.Integer(missing=0)
    jitter = ma.fields.Integer(missing=0)
    decide = ma.fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    pin = ma.fields.Integer(missing=0)
    pid = ma.fields.String()
    facts = ma.fields.List(ma.fields.Nested(FactSchema()))
    unique = ma.fields.String()
    collect = ma.fields.DateTime(format='%Y-%m-%d %H:%M:%S', default='')
    finish = ma.fields.String()
    # temp - replace with Nested(AbilitySchema)
    ability = ma.fields.Function(lambda obj: obj.ability.display,
                                 lambda obj: obj if isinstance(obj, Ability) else Ability.load(obj))
    cleanup = ma.fields.Integer(missing=0)
    visibility = ma.fields.Nested(VisibilitySchema)
    host = ma.fields.String(missing=None)
    output = ma.fields.String()

    @ma.post_load()
    def build_link(self, data, **_):
        return Link(**data)

    @ma.pre_dump()
    def prepare_link(self, data, **_):
        # temp - can be simplified with AbilitySchema
        data.executor = data.ability.executor if isinstance(data.ability, Ability) else data.ability['executor']
        return data


class Link(BaseObject):

    schema = LinkSchema()
    display_schema = LinkSchema(exclude=['jitter'])
    load_schema = LinkSchema(exclude=['decide', 'pid', 'facts', 'unique', 'collect', 'finish', 'visibility',
                                      'host', 'output'])

    @property
    def unique(self):
        return self.hash('%s' % self.id)

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

    def __init__(self, command, paw, ability, status=-3, score=0, jitter=0, cleanup=0, id=None, pin=0,
                 host=None):
        super().__init__()
        self.id = id
        self.command = command
        self.command_hash = None
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
                source_facts = operation.source.facts if operation else []
                relationships = await self._parse_link_result(result, parser, source_facts)
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

    async def _parse_link_result(self, result, parser, source_facts):
        blob = b64decode(result).decode('utf-8')
        parser_info = dict(module=parser.module, used_facts=self.used, mappers=parser.parserconfigs, source_facts=source_facts)
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
            if all((relationship.source.trait, relationship.edge, relationship.target.trait)):
                self.relationships.append(relationship)

    async def _save_fact(self, operation, fact, score):
        all_facts = operation.all_facts() if operation else self.facts
        if all([fact.trait, fact.value]) and await self._is_new_fact(fact, all_facts):
            self.facts.append(Fact(trait=fact.trait, value=fact.value, score=score, collected_by=self.paw,
                                   technique_id=self.ability.technique_id))

    async def _is_new_fact(self, fact, facts):
        return all(not self._fact_exists(fact, f) or self._is_new_host_fact(fact, f) for f in facts)

    @staticmethod
    def _fact_exists(new_fact, fact):
        return new_fact.trait == fact.trait and new_fact.value == fact.value

    def _is_new_host_fact(self, new_fact, fact):
        return new_fact.trait[:5] == 'host.' and self.paw != fact.collected_by

    async def _update_scores(self, operation, increment):
        for uf in self.used:
            all_facts = operation.all_facts() if operation else self.facts
            for found_fact in all_facts:
                if found_fact.unique == uf.unique:
                    found_fact.score += increment
                    break
