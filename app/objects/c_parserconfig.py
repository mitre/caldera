from app.utility.base_object import BaseObject


class ParserConfigException(Exception):
    pass


class ParserConfig(BaseObject):

    @property
    def display(self):
        return self.clean(dict(source=self.source, edge=self.edge, target=self.target))

    def __init__(self, source, edge=None, target=None, **kwargs):
        super().__init__()
        self.source = source
        self.edge = edge
        self.target = target
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._validate()

    def _validate(self):
        if (self.edge is None) ^ (self.target is None):
            raise ParserConfigException('Edge or Target provided without the other.')
