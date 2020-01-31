from app.utility.base_object import BaseObject


class ParserConfigException(Exception):
    pass


class ParserConfig(BaseObject):

    @classmethod
    def from_json(cls, json):
        return cls(source=json['source'], edge=json.get('edge'), target=json.get('target'))

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
        if (self.edge is None) and (self.target is not None):
            raise ParserConfigException('Target provided without an edge.')
