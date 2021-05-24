from marshmallow import fields
from marshmallow import schema


class JsonHttpErrorSchema(schema.Schema):
    error = fields.String(required=True)
    details = fields.Dict()

    class Meta:
        ordered = True

    @classmethod
    def make_dict(cls, error, details=None):
        obj = {'error': error}

        if details:
            obj['details'] = details

        return obj

    @classmethod
    def serialize(cls, error, details=None):
        mapping = cls.make_dict(error, details)
        return cls().dumps(mapping)
