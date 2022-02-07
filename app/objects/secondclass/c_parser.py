import marshmallow as ma

from app.objects.secondclass.c_parserconfig import ParserConfig, ParserConfigSchema
from app.utility.base_object import BaseObject


class ParserSchema(ma.Schema):

    module = ma.fields.String()
    parserconfigs = ma.fields.List(ma.fields.Nested(ParserConfigSchema()))

    @ma.post_load()
    def build_parser(self, data, **_):
        return Parser(**data)

    @ma.post_dump()
    def prepare_parser(self, data, **_):
        for pc, index in enumerate(data['parserconfigs']):
            if isinstance(pc, ParserConfig):
                data['parserconfigs'][index] = pc.display
        return data


class Parser(BaseObject):

    schema = ParserSchema()

    @property
    def unique(self):
        return self.module

    def __init__(self, module, parserconfigs):
        super().__init__()
        self.module = module
        self.parserconfigs = parserconfigs
