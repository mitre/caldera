import marshmallow as ma

from app.utility.base_object import BaseObject


class ParserConfigSchema(ma.Schema):

    class Meta:
        unknown = ma.INCLUDE

    source = ma.fields.String()
    edge = ma.fields.String(missing=None)
    target = ma.fields.String(missing=None)
    custom_parser_vals = ma.fields.Mapping(keys=ma.fields.String(), values=ma.fields.String())

    @ma.pre_load
    def check_edge_target(self, in_data, **_):
        if all(k in in_data.keys() for k in ['edge', 'target']) \
                and (in_data['edge'] is None) and (in_data['target'] is not None):
            raise ma.ValidationError('Target provided without an edge.')
        return in_data

    @ma.post_load()
    def build_parserconfig(self, data, **_):
        return ParserConfig(**data)

    @ma.pre_dump()
    def remove_nones(self, data, **_):
        data.source = data.source or ''
        data.edge = data.edge or ''
        data.target = data.target or ''
        data.custom_parser_vals = data.custom_parser_vals or {}
        return data


class ParserConfig(BaseObject):

    schema = ParserConfigSchema()

    def __init__(self, source, edge=None, target=None, custom_parser_vals=None):
        super().__init__()
        self.source = source
        self.edge = edge
        self.target = target
        self.custom_parser_vals = custom_parser_vals
