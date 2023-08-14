from marshmallow import fields
from marshmallow import schema

from app.objects.c_plugin import Plugin


class CalderaInfoSchema(schema.Schema):
    application = fields.String()
    version = fields.String()
    access = fields.String()
    plugins = fields.List(fields.Nested(Plugin.display_schema))

    class Meta:
        ordered = True
