import marshmallow as ma

from app.utility.base_object import BaseObject


class ResultSchema(ma.Schema):
    id = ma.fields.String()
    output = ma.fields.String()
    pid = ma.fields.String()
    status = ma.fields.String()

    @ma.post_load
    def build_result(self, data, **_):
        return Result(**data)


class Result(BaseObject):

    schema = ResultSchema()

    def __init__(self, id, output, pid=0, status=0):
        super().__init__()
        self.id = id
        self.output = output
        self.pid = pid
        self.status = status
