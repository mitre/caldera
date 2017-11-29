import math
import random
import string
from collections import defaultdict
from typing import List, Iterable
import copy
from . import wordlist


class DerefError(Exception):
    pass


class TranslateError(Exception):
    pass


class WorldObject(object):
    def __init__(self, schema, typ, obj):
        self.schema = schema
        self.typ = typ
        self._obj = obj
        self._world = None

    def attach_to_world(self, world: 'World'):
        self._world = world

    def to_dict(self):
        return copy.copy(self._obj)

    def get_world(self):
        return self._world

    @staticmethod
    def _is_derefable_field(schema, typ, field):
        if field == 'id':
            return False
        field_spec = schema[typ][field]
        if not isinstance(field_spec, dict):
            return False

        if 'list' in field_spec and ('ref' in field_spec['list'] or 'backref' in field_spec['list']):
            return True
        elif 'ref' in field_spec:
            return True
        elif 'backref' in field_spec:
            return True
        else:
            return False

    @staticmethod
    def _deref_field(schema, world, obj, field):
        field_spec = schema[obj.typ][field]
        if 'list' in field_spec and 'ref' in field_spec['list']:
            try:
                return [world.get_object_by_id(x) for x in obj._obj[field]]
            except DerefError:
                raise Exception('Could not dereference {} in {}'.format(field, obj))
        elif 'list' in field_spec and 'backref' in field_spec['list']:
            # follow the backref
            backref_spec = field_spec["list"]['backref']
            backref_typ = list(backref_spec.keys())[0]
            backref_field = list(backref_spec.values())[0]

            # search through all objects of type 'backref_typ', if the field 'backref_field' specifies this object
            # it is referenced here
            return [x for x in world.get_objects_by_type(backref_typ) if backref_field in x and x[backref_field] == obj]
        elif 'ref' in field_spec:
            if obj._obj[field] is None:
                return None
            return world.get_object_by_id(obj._obj[field])
        elif 'backref' in field_spec:
            # follow the backref
            backref_spec = field_spec['backref']
            backref_typ = list(backref_spec.keys())[0]
            backref_field = list(backref_spec.values())[0]

            # search through all objects of type 'backref_typ', if the field 'backref_field' specifies this object
            # it is referenced here
            return [x for x in world.get_objects_by_type(backref_typ) if backref_field in x and x[backref_field] == obj][0]
        else:
            raise Exception

    def __getitem__(self, key):
        if self._world and self._is_derefable_field(self.schema, self.typ, key):
            return self._deref_field(self.schema, self._world, self, key)
        return self._obj[key]

    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError:
            raise AttributeError

    def __setitem__(self, key, value):
        if isinstance(value, list):
            value = [x._obj['id'] if isinstance(x, WorldObject) else x for x in value]
        elif isinstance(value, WorldObject):
            value = value._obj['id']
        self._obj[key] = value

    def __copy__(self):
        return WorldObject(self.schema, self.typ, copy.copy(self._obj))

    def __contains__(self, item):
        return item in self._obj


class World(object):
    greek_idx = -1
    name_idx = -1
    string_base = -1
    animal_idx = -1

    @classmethod
    def _dereference(cls, typ):
        if 'ref' in typ:
            return typ['ref']
        elif 'backref' in typ:
            return list(typ['backref'].keys())[0]
        else:
            return cls._dereference(list(typ.values())[0])

    @classmethod
    def _eval_expression(cls, ex, typ, schema, objects, this_object):
        if isinstance(ex, int):
            return ex
        if isinstance(ex, str):
            if ex == '$unique_greek':
                cls.greek_idx += 1
                return wordlist.greek_alphabet[cls.greek_idx]
            if ex == '$unique_animal':
                cls.animal_idx += 1
                return wordlist.animals[cls.animal_idx]
            elif ex == '$unique_name':
                cls.name_idx += 1
                use_female = cls.name_idx % 2 == 1
                index = math.floor(cls.name_idx / 2)
                if use_female:
                    return wordlist.female_names[index]
                else:
                    return wordlist.male_names[index]
            elif ex == '$random_existing':
                obj = random.choice(objects[typ['ref']])
                return obj['id']
            else:
                return ex
        if isinstance(ex, dict):
            match = None
            if '$match' in ex:
                # values are limited to the fields in the match
                this_field, match_field = ex['$match']
                field_val = this_object[this_field]
                simple_typ = cls._dereference(typ)
                match = objects[simple_typ]
                match = [x for x in match if match_field in x and x[match_field] == field_val]
            if '$random' in ex:
                return random.randint(*ex['$random'])
            if '$random_sample' in ex:
                # create a new object of that type according to the spec
                # typ is either a ref or a backref

                if not match:
                    simple_typ = cls._dereference(typ)
                    match = objects[simple_typ]
                return [x['id'] for x in random.sample(match, ex['$random_sample'])]
            if '$new' in ex:
                # create a new object of that type according to the spec
                # typ is either a ref or a backref

                simple_typ = cls._dereference(typ)

                new_fields = []
                for x in ex['$new']['fields']:
                    new_fields.append({k: this_object[v.split(".")[1]] if isinstance(v, str) and v.startswith('$parent') else v for k, v in x.items()})

                _, new_objects = cls.build_objects(simple_typ, 1, new_fields, schema, objects)

                return new_objects[0]['id']
            if '$bool_prob' in ex:
                prob = ex['$bool_prob']
                return random.random() < prob

        raise Exception

    @classmethod
    def _eval_base_type(cls, typ):
        if typ == "string":
            cls.string_base += 1
            return string_generator(cls.string_base)
        elif typ == "int":
            cls.string_base += 1
            return cls.string_base
        else:
            return None

    @classmethod
    def build_objects(cls, typ, number, fields, schema, objects=None):
        base = schema[typ]
        new_objects = []
        if objects is None:
            objects = defaultdict(list)
        for i in range(cls._eval_expression(number, None, None, objects, None)):
            obj = {}
            objects[typ].append(obj)
            new_objects.append(obj)
            obj['id'] = 'id_' + cls._eval_base_type('string')
            for f in fields:
                field_name, field_expr = list(f.items())[0]
                try:
                    base_field_name = base[field_name]
                except KeyError:
                    print("Error: '{}.{}' field in the domain not defined in the schema".format(typ, field_name))
                    raise
                obj[field_name] = cls._eval_expression(field_expr, base_field_name, schema, objects, this_object=obj)
            for field_name, base_expr in base.items():
                if field_name not in obj:
                    obj[field_name] = cls._eval_base_type(base_expr)
                    if obj[field_name] is None and i == 0:
                        print("Warning: unspecified reference to {}.{}".format(typ, field_name))

        return objects, new_objects

    @classmethod
    def generate_domain(cls, schema, domain):
        items = None
        for d in domain:
            for name, description in d.items():
                items, _ = cls.build_objects(name, description['number'], description['fields'], schema, items)

        new_world = cls(schema)
        for typ, item_list in items.items():
            for item in item_list:
                new_world._add_object(WorldObject(schema, typ, item))
        return new_world

    def __init__(self, schema):
        self.schema = schema
        self.objects = []

    def create_object(self, typ: str, obj: dict):
        obj_copy = copy.copy(obj)
        obj_copy['id'] = 'id_' + self._eval_base_type('string')
        wo = WorldObject(self.schema, typ, obj_copy)
        self.objects.append(wo)
        wo.attach_to_world(self)
        return wo

    def _add_object(self, obj: WorldObject):
        # make sure object isn't already here
        try:
            self.get_object_by_id(obj['id'])
            raise Exception("Object has already been added")
        except DerefError:
            pass
        self.objects.append(obj)
        obj.attach_to_world(self)

    def get_all_objects(self) -> List[WorldObject]:
        return self.objects

    def get_objects_by_type(self, typ: str) -> List[WorldObject]:
        return list(filter(lambda x: x.typ == typ, self.objects))

    def get_object_by_id(self, _id: str) -> WorldObject:
        for obj in self.objects:
            if obj['id'] == _id:
                return obj
        raise DerefError("Given id is not in the world")


class MetaWorld(object):
    def __init__(self, real_world: World):
        self._real_world = real_world
        self._object_mapping = {}

    def _create_mapping(self, obj1: WorldObject, obj2: WorldObject):
        self._object_mapping[(obj1.get_world(), obj2.get_world(), obj1)] = obj2
        self._object_mapping[(obj2.get_world(), obj1.get_world(), obj2)] = obj1

    def translate_object(self, obj: WorldObject, to_world: World) -> WorldObject:
        try:
            return self._object_mapping[(obj.get_world(), to_world, obj)]
        except KeyError:
            raise TranslateError

    def translate_object_to_real_world(self, obj: WorldObject):
        return self.translate_object(obj, self._real_world)

    def get_real_world(self):
        return self._real_world

    def get_sub_world(self):
        return World(self._real_world.schema)

    def _translate_references(self, src_world: World, dest_world: World, typ: str, obj: dict):
        schema = self._real_world.schema
        translated = {}
        for field in obj:
            field_spec = schema[typ][field]
            if 'list' in field_spec and 'ref' in field_spec['list']:
                try:
                    translated[field] = [self.translate_object(src_world.get_object_by_id(x), dest_world)["id"] for x in obj[field]]
                except DerefError:
                    raise
            elif 'list' in field_spec and 'backref' in field_spec['list']:
                translated[field] = None
            elif 'ref' in field_spec:
                if obj[field] is None:
                    translated[field] = None
                else:
                    try:
                        translated[field] = self.translate_object(src_world.get_object_by_id(obj[field]), dest_world)["id"]
                    except TranslateError:
                        raise
                    except DerefError:
                        raise
            elif 'backref' in field_spec:
                translated[field] = None
            else:
                translated[field] = obj[field]

        return translated

    def _obj_dict_to_ref(self, obj_dict):
        for field in obj_dict:
            if isinstance(obj_dict[field], WorldObject):
                obj_dict[field] = obj_dict[field]["id"]
            elif isinstance(obj_dict[field], list):
                obj_dict[field] = [x['id'] if isinstance(x, WorldObject) else x for x in obj_dict[field]]
            else:
                obj_dict[field] = obj_dict[field]
        return obj_dict

    def create(self, sub_world: World, typ: str, obj_dict: dict):
        """Creates an object in the sub_world, also creating it in the real_world"""
        obj_dict = self._obj_dict_to_ref(obj_dict)
        real_world_obj = self._real_world.create_object(typ, obj_dict)
        obj_dict = self._translate_references(self._real_world, sub_world, typ, obj_dict)
        sub_world_obj = sub_world.create_object(typ, obj_dict)
        self._create_mapping(real_world_obj, sub_world_obj)

    def know(self, sub_world: World, real_world_obj: WorldObject, fields: Iterable[str]):
        """Moves an object and its properties from the real world to the subworld"""
        obj_dict = {field: real_world_obj[field] for field in fields}
        obj_dict = self._obj_dict_to_ref(obj_dict)
        obj_dict = self._translate_references(self._real_world, sub_world, real_world_obj.typ, obj_dict)

        try:
            sub_world_obj = self.translate_object(real_world_obj, sub_world)
            # if this object already exists in the subworld, just update its properties
            sub_world_obj._obj.update(obj_dict)
        except TranslateError:
            # doesn't yet exist in the subworld, so create it completely
            sub_world_obj = sub_world.create_object(real_world_obj.typ, obj_dict)
            self._create_mapping(real_world_obj, sub_world_obj)
        return sub_world_obj


def string_generator(num):
    accum = ""

    while True:
        accum = string.ascii_lowercase[num % 26] + accum
        num //= 26
        if num == 0:
            return accum
