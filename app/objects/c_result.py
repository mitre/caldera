from app.objects.base_object import BaseObject


class Result(BaseObject):

    @property
    def unique(self):
        return True

    def display(self):
        return dict(output=self.output, parsed=self.parsed)

    def __init__(self, output, parsed=None):
        self.output = output
        self.parsed = parsed

    def store(self, ram):
        pass
