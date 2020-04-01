from collections import namedtuple

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_fact import FactSchema
from app.objects.secondclass.c_rule import RuleSchema
from app.utility.base_object import BaseObject


class AdjustmentSchema(ma.Schema):

    ability_id = ma.fields.String()
    trait = ma.fields.String()
    value = ma.fields.String()
    offset = ma.fields.Integer()

    @ma.post_load()
    def build_adjustment(self, data, **_):
        return Adjustment(**data)


Adjustment = namedtuple('Adjustment', 'ability_id trait value offset')


class SourceSchema(ma.Schema):

    id = ma.fields.String()
    name = ma.fields.String()
    facts = ma.fields.List(ma.fields.Nested(FactSchema()))
    rules = ma.fields.List(ma.fields.Nested(RuleSchema()))
    adjustments = ma.fields.List(ma.fields.Nested(AdjustmentSchema(), required=False))

    @ma.pre_load
    def fix_adjustments(self, in_data, **_):
        x = []
        raw_adjustments = in_data.pop('adjustments', {})
        if raw_adjustments:
            for ability_id, adjustments in raw_adjustments.items():
                for trait, block in adjustments.items():
                    for change in block:
                        x.append(dict(ability_id=ability_id, trait=trait, value=change.get('value'),
                                      offset=change.get('offset')))
        in_data['adjustments'] = x
        return in_data

    @ma.post_load()
    def build_source(self, data, **_):
        data['identifier'] = data.pop('id')
        return Source(**data)


class Source(FirstClassObjectInterface, BaseObject):

    schema = SourceSchema()
    display_schema = SourceSchema(exclude=('adjustments',))

    @property
    def unique(self):
        return self.hash('%s' % self.id)

    def __init__(self, identifier, name, facts, rules=(), adjustments=()):
        super().__init__()
        self.id = identifier
        self.name = name
        self.facts = facts
        self.rules = rules
        self.adjustments = adjustments

    def store(self, ram):
        existing = self.retrieve(ram['sources'], self.unique)
        if not existing:
            ram['sources'].append(self)
            return self.retrieve(ram['sources'], self.unique)
        existing.update('name', self.name)
        existing.update('facts', self.facts)
        existing.update('rules', self.rules)
        return existing
