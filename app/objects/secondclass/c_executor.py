import marshmallow as ma

from app.utility.base_object import BaseObject

from app.objects.secondclass.c_parser import ParserSchema
from app.objects.secondclass.c_variation import Variation, VariationSchema


class ExecutorSchema(ma.Schema):
    name = ma.fields.String(load_default=None)
    platform = ma.fields.String(load_default=None)
    command = ma.fields.String(load_default=None)
    code = ma.fields.String(load_default=None)
    language = ma.fields.String(load_default=None)
    build_target = ma.fields.String(load_default=None)
    payloads = ma.fields.List(ma.fields.String())
    uploads = ma.fields.List(ma.fields.String())
    timeout = ma.fields.Int(load_default=60)
    parsers = ma.fields.List(ma.fields.Nested(ParserSchema()))
    cleanup = ma.fields.List(ma.fields.String())
    variations = ma.fields.List(ma.fields.Nested(VariationSchema()))
    additional_info = ma.fields.Dict(keys=ma.fields.String(), values=ma.fields.String())

    @ma.post_load
    def build_executor(self, data, **_):
        return Executor(**data)


class Executor(BaseObject):

    schema = ExecutorSchema()
    display_schema = ExecutorSchema()

    RESERVED = dict(payload='#{payload}')

    HOOKS = dict()

    @classmethod
    def is_global_variable(cls, variable):
        return variable in cls.RESERVED

    @property
    def test(self):
        """Get command with app property variables replaced"""
        return self.decode_bytes(self.replace_app_props(self.encode_string(self.command)))

    def __init__(self, name, platform, command=None, code=None, language=None, build_target=None,
                 payloads=None, uploads=None, timeout=60, parsers=None, cleanup=None, variations=None,
                 additional_info=None, **kwargs):
        super().__init__()
        self.name = name
        self.platform = platform.lower()

        self.command = command
        self.code = code
        self.language = language
        self.build_target = build_target

        self.payloads = payloads if payloads else []
        self.uploads = uploads if uploads else []

        self.timeout = timeout
        self.parsers = parsers if parsers else []

        if not cleanup:
            self.cleanup = []
        elif isinstance(cleanup, str):
            self.cleanup = [cleanup]
        else:
            self.cleanup = cleanup

        self.variations = get_variations(variations)

        self.additional_info = additional_info or dict()
        self.additional_info.update(**kwargs)

    def __getattr__(self, item):
        try:
            return super().__getattribute__('additional_info')[item]
        except KeyError:
            raise AttributeError(item)

    def replace_cleanup(self, command, payload):
        return command.replace(self.RESERVED['payload'], payload)


def get_variations(data):
    variations = []
    if not data:
        return []
    for v in data:
        if isinstance(v, Variation):
            description = v.description
            command = v.command
        else:
            description = v['description']
            command = v['command']
        variations.append(Variation.load(dict(description=description, command=command)))
    return variations
