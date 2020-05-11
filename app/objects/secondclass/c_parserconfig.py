import marshmallow as ma

from app.utility.base_object import BaseObject


class ParserConfigSchema(ma.Schema):

    source = ma.fields.String()
    edge = ma.fields.String()
    target = ma.fields.String()
    extra_attrs = ma.fields.Dict()

    @ma.pre_load
    def check_edge_target(self, in_data, **_):
        if all(k in in_data.keys() for k in ['edge', 'target']) \
                and (in_data['edge'] is None) and (in_data['target'] is not None):
            raise ma.ValidationError('Target provided without an edge.')
        return in_data

    @ma.post_load()
    def build_parserconfig(self, data, **_):
        return ParserConfig(**data)


class ParserConfig(BaseObject):

    schema = ParserConfigSchema(unknown=ma.INCLUDE)

    def __init__(self, source, edge=None, target=None, **kwargs):
        super().__init__()
        self.source = source
        self.edge = edge
        self.target = target
        for k, v in kwargs.items():
            setattr(self, k, v)
