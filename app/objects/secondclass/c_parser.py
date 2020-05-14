import marshmallow as ma

from app.objects.secondclass.c_parserconfig import ParserConfig, ParserConfigSchema
from app.utility.base_object import BaseObject


class ParserSchema(ma.Schema):

    module = ma.fields.String()
    parserconfigs = ma.fields.List(ma.fields.Nested(ParserConfigSchema()))

    @ma.pre_load
    def fix_relationships(self, parser, **_):
        if 'relationships' in parser:
            parser['parserconfigs'] = parser.pop('relationships')
        return parser

    @ma.post_load()
    def build_parser(self, data, **_):
        return Parser(**data)

    @ma.post_dump()
    def prepare_parser(self, data, **_):
        data['relationships'] = data.pop('parserconfigs')
        for pc, index in enumerate(data['relationships']):
            if isinstance(pc, ParserConfig):
                data['relationships'][index] = pc.display
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
