import marshmallow as ma
from marshmallow import fields


class ConfigUpdateSchema(ma.Schema):
    prop = fields.String(required=True)
    value = fields.String(required=True)

    @ma.validates('prop')
    def validate_prop(self, value):
        if not value:
            raise ma.ValidationError('prop cannot be empty')


class AgentConfigUpdateSchema(ma.Schema):
    sleep_min = fields.Integer()
    sleep_max = fields.Integer()
    watchdog = fields.Integer()
    untrusted_timer = fields.Integer()
    implant_name = fields.String()
    bootstrap_abilities = fields.List(fields.String)
    deadman_abilities = fields.List(fields.String)
