import marshmallow as ma

from app.utility.base_object import BaseObject


class ProcessorSchema(ma.Schema):

    module = ma.fields.String()

    @ma.post_load()
    def build_processor(self, data, **_):
        return Processor(**data)

    @ma.post_dump()
    def prepare_processor(self, data, **_):
        return data


class Processor(BaseObject):

    schema = ProcessorSchema()

    @property
    def unique(self):
        return self.module

    def __init__(self, module):
        super().__init__()
        self.module = module
