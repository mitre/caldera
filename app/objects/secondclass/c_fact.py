import marshmallow as ma

from datetime import datetime
from enum import Enum

from app.utility.base_object import BaseObject

escape_ref = {
    'sh': {
        'special': ['\\', ' ', '$', '#', '^', '&', '*', '|', '`', '>',
                    '<', '"', '\'', '[', ']', '{', '}', '?', '~', '%'],
        'escape_prefix': '\\'
    },
    'psh': {
        'special': ['`', '^', '(', ')', '[', ']', '|', '+', '%',
                    '?', '$', '#', '&', '@', '>', '<', '\'', '"', ' '],
        'escape_prefix': '`'
    },
    'cmd': {
        'special': ['^', '&', '<', '>', '|', ' ', '?', '\'', '"'],
        'escape_prefix': '^'
    }
}


class FactLacksIdentifier(Exception):
    pass


NOT_SPECIFIED = "X"


class SourceTypes(Enum):
    DOMAIN = 1
    SEEDED = 2
    LEARNED = 3
    IMPORTED = 4


class Restrictions(Enum):
    UNIQUE = 1
    SINGLE = 2


class FactSchema(ma.Schema):

    unique = ma.fields.String()
    name = ma.fields.String()
    value = ma.fields.Function(lambda x: x.value, deserialize=lambda x: str(x), allow_none=True)
    timestamp = ma.fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    __source_type = ma.fields.Int()
    source = ma.fields.String()
    links = ma.fields.List(ma.fields.String())
    __restrictions = ma.fields.Int()
    relationships = ma.fields.List(ma.fields.String())
    score = ma.fields.Integer()
    technique_id = ma.fields.String()

    @ma.pre_load
    def test_input(self, data, **_):
        if "trait" in data:
            print(f"Warning - the trait argument is being replaced with 'name' as part of the fact upgrade.")
            data['name'] = data.pop('trait')
        if "collected_by" in data:
            print(f"Warning - removing collected_by")
            data.pop('collected_by')
        return data

    @ma.post_load
    def build_fact(self, data, **_):
        if "trait" in data:  # This is a temporary workaround until the fact upgrades are completed
            print(f"Warning - the trait argument is being replaced with 'name' as part of the fact upgrade.")
            return Fact(**{"name" if k == "trait" else k: v for k, v in data.items()})
        else:
            return Fact(**data)


class Fact(BaseObject):

    schema = FactSchema()
    load_schema = FactSchema(exclude=['unique'])

    @property
    def display(self):
        default = super().display
        default['relationships'] = [x.display for x in self.relationships]
        default['relationships'] = [dict(source=f"{x['source'].name}: {x['source'].value}", edge=x['edge'],
                                         target=f"{x['target'].name}: {x['target'].value}")
                                    for x in default['relationships'] if x['edge'] != '']
        default['links'] = [dict(host=x.host, paw=x.paw, id=x.id) for x in self.links]
        default['source_type'] = self.source_type.name
        return default

    @property
    def unique(self):
        return self.hash('%s%s' % (self.name, self.value))

    def escaped(self, executor):
        if executor not in escape_ref:
            return self.value
        escaped_value = str(self.value)
        for char in escape_ref[executor]['special']:
            escaped_value = escaped_value.replace(char, (escape_ref[executor]['escape_prefix'] + char))
        return escaped_value

    def __eq__(self, other):
        if isinstance(other, Fact):
            return self.unique == other.unique
        return False

    def __init__(self, name, value=None, source_type=SourceTypes["LEARNED"], source=NOT_SPECIFIED,
                 restrictions=NOT_SPECIFIED, score=1, technique_id=None):
        super().__init__()
        self.name = name
        self.value = value
        self.timestamp = datetime.now()
        self.__source_type = source_type
        self.source = source
        self.links = list()
        self.__restrictions = restrictions
        self.relationships = list()
        self.score = score
        self.technique_id = technique_id

    @property
    def collected_by(self):  # collected_by is functionally the paw of the agent that acquired this
        print(f"collected_by will be deprecated. Please use source/links instead.")
        if len(self.links):
            return self.links[0].paw
        return None

    # Temporary reroute as the fact upgrade continues
    @property
    def trait(self):
        print(f"trait will be deprecated. Please use 'name' instead.")
        return self.name

    @property
    def source_type(self):
        return self.__source_type

    @source_type.setter
    def source_type(self, s_type):
        if s_type in SourceTypes:
            self.__source_type = s_type
        else:
            print(f"{s_type} is not a valid SourceType. Defaulting to 'LEARNED'")
            self.__source_type = SourceTypes["LEARNED"]

    @property
    def restrictions(self):
        return self.__restrictions

    @restrictions.setter
    def restrictions(self, restriction):
        if restriction in Restrictions:
            self.restrictions = restriction
        else:
            print(f"{restriction} is not a valid Restriction.")

    def add_link(self, link):
        if link:
            if any(x.id == link.id for x in self.links):
                print(f"This fact already has connections to link {link.id}")
                return
            self.links.append(link)

    def add_relationship(self, relationship):
        if relationship:
            if any(x.unique == relationship.unique for x in self.relationships):
                print(f"This fact already has connections to relationship {relationship.unique}")
                return
            self.relationships.append(relationship)
