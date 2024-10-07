from marshmallow import fields, schema


class PayloadQuerySchema(schema.Schema):
    sort = fields.Boolean(required=False, load_default=False)
    exclude_plugins = fields.Boolean(required=False, load_default=False)
    add_path = fields.Boolean(required=False, load_default=False)


class PayloadSchema(schema.Schema):
    payloads = fields.List(fields.String())


class PayloadCreateRequestSchema(schema.Schema):
    file = fields.Raw(required=True, metadata={'type': 'file'})


class PayloadDeleteRequestSchema(schema.Schema):
    name = fields.String(required=True)
