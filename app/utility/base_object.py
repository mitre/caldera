from app.utility.base_world import BaseWorld


class BaseObject(BaseWorld):

    def match(self, criteria):
        if not criteria:
            return self
        criteria_matches = [True for k, v in criteria.items() if self.__getattribute__(k) == v]
        if len(criteria_matches) == len(criteria) and all(criteria_matches):
            return self

    def update(self, field, value):
        if value:
            self.__setattr__(field, value)

    @staticmethod
    def retrieve(collection, unique):
        return next((i for i in collection if i.unique == unique), None)

    @staticmethod
    def hash(s):
        return s

    @staticmethod
    def clean(d):
        for k, v in d.items():
            if v is None:
                d[k] = ''
        return d
