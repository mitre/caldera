from app.utility.base_object import BaseObject


class Result(BaseObject):

    def __init__(self, id, output, pid=0, status=0):
        super().__init__()
        self.id = id
        self.output = output
        self.pid = pid
        self.status = status
