import marshmallow as ma

from app.utility.base_object import BaseObject


class InstructionSchema(ma.Schema):
    id = ma.fields.String()
    sleep = ma.fields.Int()
    command = ma.fields.String()
    executor = ma.fields.String()
    timeout = ma.fields.Int()
    payloads = ma.fields.List(ma.fields.String())

    @ma.post_load
    def build_instruction(self, data, **_):
        return Instruction(**data)


class Instruction(BaseObject):

    schema = InstructionSchema()

    @property
    def display(self):
        return self.clean(dict(id=self.id, sleep=self.sleep, command=self.command, executor=self.executor,
                               timeout=self.timeout, payloads=self.payloads))

    def __init__(self, id, command, executor, payloads=None, sleep=0, timeout=60):
        super().__init__()
        self.id = id
        self.sleep = sleep
        self.command = command
        self.executor = executor
        self.timeout = timeout
        self.payloads = payloads if payloads else []
