import marshmallow as ma
from marshmallow import fields


class DeployCommandsSchema(ma.Schema):
    abilities = fields.List(fields.Dict)
    app_config = fields.Dict()
