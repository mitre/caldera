import re

from app.utility.base_world import BaseWorld


class BaseObject(BaseWorld):

    schema = None
    display_schema = None
    load_schema = None

    def __init__(self):
        self._access = self.Access.APP
        self._created = self.get_current_timestamp()

    def match(self, criteria):
        if not criteria:
            return self
        criteria_matches = []
        for k, v in criteria.items():
            if type(v) is tuple:
                for val in v:
                    if getattr(self, k) == val:
                        criteria_matches.append(True)
            else:
                if getattr(self, k) == v:
                    criteria_matches.append(True)
        if len(criteria_matches) >= len(criteria) and all(criteria_matches):
            return self

    def update(self, field, value):
        """
        Updates the given field to the given value as long as the value is not None and the new value is different from
        the current value. Ignoring None prevents current property values from being overwritten to None if the given
        property is not intentionally passed back to be updated (example: Agent heartbeat)

        :param field: object property to update
        :param value: value to update to
        """
        if (value is not None) and (value != self.__getattribute__(field)):
            self.__setattr__(field, value)

    def search_tags(self, value):
        tags = getattr(self, 'tags', None)
        if tags and value in tags:
            return True

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

    @property
    def access(self):
        return self._access

    @property
    def created(self):
        return self._created

    @property
    def display(self):
        if self.display_schema:
            dumped = self.display_schema.dump(self)
        elif self.schema:
            dumped = self.schema.dump(self)
        else:
            raise NotImplementedError
        return self.clean(dumped)

    @access.setter
    def access(self, value):
        self._access = value

    @created.setter
    def created(self, value):
        self._created = value

    def replace_app_props(self, encoded_string):
        if encoded_string:
            decoded_test = self.decode_bytes(encoded_string)
            for k, v in self.get_config().items():
                if k.startswith('app.'):
                    re_variable = re.compile(r'#{(%s.*?)}' % k, flags=re.DOTALL)
                    decoded_test = re.sub(re_variable, str(v).strip(), decoded_test)
            return self.encode_string(decoded_test)

    @classmethod
    def load(cls, dict_obj):
        if cls.load_schema:
            return cls.load_schema.load(dict_obj)
        elif cls.schema:
            return cls.schema.load(dict_obj)
        else:
            raise NotImplementedError
