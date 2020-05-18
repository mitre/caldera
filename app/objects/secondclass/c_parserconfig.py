import marshmallow as ma

from app.utility.base_object import BaseObject


class ParserConfigSchema(ma.Schema):

    class Meta:
        unknown = ma.INCLUDE

    source = ma.fields.String()
    edge = ma.fields.String(missing=None)
    target = ma.fields.String(missing=None)

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
        data.source = data.source if data.source else ''
        data.edge = data.edge if data.edge else ''
        data.target = data.target if data.target else ''
        return data


class ParserConfig(BaseObject):

    schema = ParserConfigSchema()

    def __init__(self, source, edge=None, target=None, **kwargs):
        super().__init__()
        self.source = source
        self.edge = edge
        self.target = target
        for k, v in kwargs.items():
            setattr(self, k, v)
