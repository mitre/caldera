from marshmallow import fields, schema


class PayloadQuerySchema(schema.Schema):
    sort = fields.Boolean(required=False, default=False)
    exclude_plugins = fields.Boolean(required=False, default=False)
    add_path = fields.Boolean(required=False, default=False)


class PayloadSchema(schema.Schema):
    payloads = fields.List(fields.String())


class PayloadCreateRequestSchema(schema.Schema):
    file = fields.Raw(type="file", required=True)


class PayloadDeleteRequestSchema(schema.Schema):
    name = fields.String(required=True)
