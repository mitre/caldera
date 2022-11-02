from abc import abstractmethod

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.utility.base_object import BaseObject


class DataEncoderSchema(ma.Schema):
    name = ma.fields.String()
    description = ma.fields.String()
    module = ma.fields.String()


class DataEncoder(FirstClassObjectInterface, BaseObject):
    schema = DataEncoderSchema()
    display_schema = DataEncoderSchema(exclude=['module'])

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    def __init__(self, name, description):
        super().__init__()
        self.name = name
        self.description = description

    def store(self, ram):
        existing = self.retrieve(ram['data_encoders'], self.unique)
        if not existing:
            ram['data_encoders'].append(self)
            return self.retrieve(ram['data_encoders'], self.unique)
        return existing

    @abstractmethod
    def encode(self, data, **_):
        raise NotImplementedError

    @abstractmethod
    def decode(self, data, **_):
        raise NotImplementedError
