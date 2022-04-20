import marshmallow as ma

from app.utility.base_object import BaseObject


class InstructionSchema(ma.Schema):
    id = ma.fields.String()
    sleep = ma.fields.Int()
    command = ma.fields.String()
    executor = ma.fields.String()
    timeout = ma.fields.Int()
    payloads = ma.fields.List(ma.fields.String())
    deadman = ma.fields.Boolean()
    uploads = ma.fields.List(ma.fields.Dict(keys=ma.fields.String(), values=ma.fields.String()))
    delete_payload = ma.fields.Bool(missing=None)

    @ma.post_load
    def build_instruction(self, data, **_):
        return Instruction(**data)


class Instruction(BaseObject):

    schema = InstructionSchema()

    @property
    def display(self):
        return self.clean(dict(id=self.id, sleep=self.sleep, command=self.command, executor=self.executor,
                               timeout=self.timeout, payloads=self.payloads, uploads=self.uploads, deadman=self.deadman,
                               delete_payload=self.delete_payload))

    def __init__(self, id, command, executor, payloads=None, uploads=None, sleep=0, timeout=60, deadman=False, delete_payload=True):
        super().__init__()
        self.id = id
        self.sleep = sleep
        self.command = command
        self.executor = executor
        self.timeout = timeout
        self.payloads = payloads if payloads else []
        self.uploads = uploads if uploads else []
        self.deadman = deadman
        self.delete_payload = delete_payload
