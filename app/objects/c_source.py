from collections import namedtuple
import uuid

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_fact import FactSchema, OriginType
from app.objects.secondclass.c_rule import RuleSchema
from app.objects.secondclass.c_relationship import RelationshipSchema
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
    facts = ma.fields.List(ma.fields.Nested(FactSchema))
    rules = ma.fields.List(ma.fields.Nested(RuleSchema))
    adjustments = ma.fields.List(ma.fields.Nested(AdjustmentSchema))
    relationships = ma.fields.List(ma.fields.Nested(RelationshipSchema))
    plugin = ma.fields.String(missing=None)

    @ma.pre_load
    def fix_adjustments(self, in_data, **_):
        x = []
        raw_adjustments = in_data.pop('adjustments', {})
        if raw_adjustments and type(raw_adjustments) == dict:
            for ability_id, adjustments in raw_adjustments.items():
                for trait, block in adjustments.items():
                    for change in block:
                        x.append(dict(ability_id=ability_id, trait=trait, value=change.get('value'),
                                      offset=change.get('offset')))
        in_data['adjustments'] = x
        self._fix_loaded_object_origins(in_data)
        return in_data

    @ma.post_load()
    def build_source(self, data, **kwargs):
        return None if kwargs.get('partial') is True else Source(**data)

    @staticmethod
    def _fix_loaded_object_origins(input_data):
        """
        Sort through input_data's facts and relationships, and patch them to include origin and references
        :param input_data: A 'source' dictionary
        :return: input_data with updated facts/relationships (patched in place)
        """
        if 'facts' in input_data:
            for y in input_data['facts']:
                y['origin_type'] = OriginType.IMPORTED.name
                y['source'] = input_data['id']
        if 'relationships' in input_data:
            for y in input_data['relationships']:
                y['source']['origin_type'] = OriginType.IMPORTED.name
                y['source']['source'] = input_data['id']
                if 'target' in y:
                    y['target']['origin_type'] = OriginType.IMPORTED.name
                    y['target']['source'] = input_data['id']


class Source(FirstClassObjectInterface, BaseObject):

    schema = SourceSchema()
    display_schema = SourceSchema(exclude=('adjustments',))

    @property
    def unique(self):
        return self.hash('%s' % self.id)

    def __init__(self, name='', id='', facts=(), relationships=(), rules=(), adjustments=(), plugin=''):
        super().__init__()
        self.id = id if id else str(uuid.uuid4())
        self.name = name
        self.facts = facts
        self.rules = rules
        self.adjustments = adjustments
        self.relationships = relationships
        self.plugin = plugin

    def store(self, ram):
        existing = self.retrieve(ram['sources'], self.unique)
        if not existing:
            ram['sources'].append(self)
            return self.retrieve(ram['sources'], self.unique)
        existing.update('name', self.name)
        existing.update('facts', self.facts)
        existing.update('rules', self.rules)
        existing.update('relationships', self.relationships)
        existing.update('plugin', self.plugin)
        return existing
