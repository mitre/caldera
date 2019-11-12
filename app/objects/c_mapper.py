from app.utility.base_object import BaseObject


class Mapper(BaseObject):

    @property
    def unique(self):
        uniq = ""
        for f in self.fields:
            uniq = uniq + getattr(self, f)
        return uniq

    @property
    def display(self):
        attrs = {}
        for f in self.fields:
            attrs[f] = getattr(self, f)
        return self.clean(attrs)

    def __init__(self, **kwargs):
        self.source = kwargs["source"]
        self.edge = None
        self.target = None
        self.fields = []
        for k, v in kwargs.items():
            self.fields.append(k)
            setattr(self, k, v)
        for f in ["edge", "source"]:
            if f not in self.fields:
                self.fields.append(f)
        self.fields.sort()
