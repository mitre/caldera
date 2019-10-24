import hashlib


class BaseObject:

    def match(self, criteria):
        if not criteria:
            return self
        for k,v in criteria.items():
            if self.__getattribute__(k) == v:
                return self

    def update(self, field, value):
        if value:
            self.__setattr__(field, value)

    @staticmethod
    def retrieve(collection, unique):
        return next((i for i in collection if i.unique == unique), None)

    @staticmethod
    def hash(s):
        return hashlib.md5(s.encode())
