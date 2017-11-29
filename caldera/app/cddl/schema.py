from collections import ChainMap
from .util import Variable
from collections import defaultdict


class VarStoreError(Exception):
    pass


class VarStore(object):
    def __init__(self, schema):
        self.count = -1
        self.lookup = ChainMap()
        self.type_of_var = {}
        self.schema = schema
        self.constants = set()
        self.backrefs = build_links(schema)

    def define_root(self, typ, key=None, prefix=None):
        """Define a new variable.
        Args:
            key: a name to associate the variable with
            typ: the type of the variable, if it is not defined the type will be inferred from the key.
            prefix: a prefix to use when generating the variable's name
            """
        if typ is None:
            raise VarStoreError("Root vars must have a defined type")
        if key is not None:
            assert '.' not in key

        if prefix is None:
            prefix = 'V'

        try:
            typ, var = self.lookup[key]
            return var
        except KeyError:
            self.count += 1
            count_str = str(self.count)
            if len(count_str) == 1:
                count_str = '0' + count_str
            if key is None:
                key = 'ANON' + count_str
            v = Variable(prefix + count_str)

            self.lookup[key] = (typ, v)

            self.type_of_var[v] = typ
            return v

    def define(self, key=None, typ=None, prefix=None):
        """Define a new variable.
        Args:
            key: a name to associate the variable with
            typ: the type of the variable, if it is not defined the type will be inferred from the key.
            prefix: a prefix to use when generating the variable's name
            """

        if key is not None:
            assert '.' in key

        if prefix is None:
            prefix = 'V'
        try:
            typ, var = self.lookup[key]
            return var
        except KeyError:
            self.count += 1
            count_str = str(self.count)
            if len(count_str) == 1:
                count_str = '0' + count_str
            if key is None:
                key = 'ANON' + count_str
            v = Variable(prefix + count_str)

            if typ is None:
                typ = self.find_type(key)
            self.type_of_var[v] = typ

            # insert into the level that contains the root
            if '.' in key:
                root = key.split('.')[0]
                for d in self.lookup.maps:
                    if root in d:
                        d[key] = (typ, v)
                        break
            else:
                self.lookup[key] = (typ, v)

            return v

    def find_var(self, key):
        return self.lookup[key][1]

    def find_type(self, key):
        key_split = key.split('.')
        top_var = key_split[0]
        descendants = '.'.join(key_split[1:])
        typ, _ = self.lookup[top_var]
        return type_lookup(self.schema, typ, descendants)

    def find_raw_type(self, key):
        key_split = key.split('.')
        top_var = key_split[0]
        typ, _ = self.lookup[top_var]

        for part in key_split[1:]:
            typ = self.schema[type_deref(typ)][part]
        return typ

    def find_type_of_var(self, var):
        return self.type_of_var[var]

    def descend_scope(self):
        self.lookup = self.lookup.new_child()

    def ascend_scope(self):
        self.lookup = self.lookup.parents

    def define_constant(self, constant):
        self.constants.add(constant)

    def type_has_backrefs(self, typ):
        for rtyp, field in self.backrefs.keys():
            if rtyp == typ:
                return True
        return False


def build_links(schema):
    refs = defaultdict(list)
    for obj_type, defn in schema.items():
        for field, field_type in defn.items():
            if 'backref' in field_type:
                ref_type, ref_field = list(field_type['backref'].items())[0]
                refs[(ref_type, ref_field)].append(('item', obj_type, field))
                refs[(obj_type, field)].append(('item', ref_type, ref_field))
            elif 'list' in field_type and 'backref' in field_type['list']:
                ref_type, ref_field = list(field_type['list']['backref'].items())[0]
                refs[(ref_type, ref_field)].append(('list', obj_type, field))
                refs[(obj_type, field)].append(('item', ref_type, ref_field))
    return refs


def type_deref(typ):
    if 'list' in typ:
        typ = typ['list']
    if 'ref' in typ:
        typ = typ['ref']
    if 'backref' in typ:
        typ = list(typ['backref'].keys())[0]
    return typ


def type_lookup(schema, typ, stem):
    parts = []
    if stem:
        parts = stem.split(".")
    for part in parts:
        typ = type_deref(schema[typ][part])
    return typ


class PredicateError(Exception):
    pass


class PredicateRegistry(object):
    def __init__(self, schema):
        self.finalized = False
        self.registry = defaultdict(list)
        self.registered_predicates = {}
        self.field_type = {}
        self._build_registry(schema)
        self.used_predicates = set()

    def _build_registry(self, schema):
        if self.finalized:
            raise PredicateError
        for obj_type in schema:
            for field_name, field_type in schema[obj_type].items():
                self.registry[field_name].append((field_type, obj_type))
                self.field_type[(obj_type, field_name)] = type_deref(field_type)

        self._finalize()

    def _finalize(self):
        for field_name, items in self.registry.items():
            if len(items) == 1:
                field_type, obj_type = items[0]
                if 'list' in field_type:
                    self.registered_predicates[(obj_type, field_name)] = ('mem', field_name)
                else:
                    self.registered_predicates[(obj_type, field_name)] = ('prop', field_name)
            else:
                for field_type, obj_type in items:
                    if 'list' in field_type:
                        self.registered_predicates[(obj_type, field_name)] = ('mem', obj_type, field_name)
                    else:
                        self.registered_predicates[(obj_type, field_name)] = ('prop', obj_type, field_name)

        self.finalized = True

    def get_predicate(self, obj_type, field_name, prefix=''):
        if not self.finalized:
            raise PredicateError
        self.used_predicates.add((obj_type, field_name))
        return prefix + '_'.join([str(x) for x in self.registered_predicates[(obj_type, field_name)]])

    def get_backlinks(self, vs: VarStore, obj_type, field_name):
        backrefs = vs.backrefs[(obj_type, field_name)]
        return [(op, self.get_predicate(target_type, target_prop))for op, target_type, target_prop in backrefs]
