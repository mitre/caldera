import marshmallow as ma

from app.utility.base_object import BaseObject


class ResultSchema(ma.Schema):
    id = ma.fields.String()
    output = ma.fields.String()
    pid = ma.fields.String()
    status = ma.fields.String()
    agent_reported_time = ma.fields.DateTime(format='%Y-%m-%d %H:%M:%S')

    @ma.post_load
    def build_result(self, data, **_):
        return Result(**data)


class Result(BaseObject):

    schema = ResultSchema()

    def __init__(self, id, output, pid=0, status=0, agent_reported_time=None):
        super().__init__()
        self.id = id
        self.output = output
        self.pid = pid
        self.status = status
        self.agent_reported_time = agent_reported_time
