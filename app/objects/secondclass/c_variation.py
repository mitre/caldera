import marshmallow as ma

from app.utility.base_object import BaseObject


class VariationSchema(ma.Schema):

    description = ma.fields.String()
    command = ma.fields.String()

    @ma.post_load
    def build_variation(self, data, **_):
        return Variation(**data)


class Variation(BaseObject):

    schema = VariationSchema()

    @property
    def command(self):
        return self.replace_app_props(self._command)

    def __init__(self, description, command):
        super().__init__()
        self.description = description
        self._command = self.encode_string(command)
