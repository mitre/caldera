from marshmallow import fields
from marshmallow import schema


class BaseGetAllQuerySchema(schema.Schema):
    sort = fields.String(required=False)
    include = fields.List(fields.String, required=False)
    exclude = fields.List(fields.String, required=False)


class BaseGetOneQuerySchema(schema.Schema):
    include = fields.List(fields.String, required=False)
    exclude = fields.List(fields.String, required=False)
