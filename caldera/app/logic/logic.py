import re
import time
from typing import List, Iterable, Set, Tuple, Union
from collections import defaultdict
from itertools import product

from unification import unifiable

from ..operation.step import OPVar, Step
from ..engine import objects as db
from ..util import CaseException
from ..cddl.build_ast import get_ast


# convert steps to logic predicates
class Expression(object):
    pass


@unifiable
class Variable(Expression):
    def __init__(self, name: str=None):
        if not name:
            name = 'X{}'.format(int(time.process_time()*10000000))
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.name)

    def __lt__(self, other):
        return str(self) < str(other)


class Comparison(Expression):
    def __init__(self, comparator: str, obj1: Expression, obj2: Expression):
        self.comparator = comparator
        self.obj1 = obj1
        self.obj2 = obj2

    def __str__(self):
        return "{} {} {}".format(self.obj1, self.comparator, self.obj2)

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))


class Unary(Expression):
    def __init__(self, operator: str, obj1: Expression):
        self.operator = operator
        self.obj1 = obj1

    def __str__(self):
        return "{} {}".format(self.operator, self.obj1)

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))


@unifiable
class Term(Expression):
    def __str__(self):
        return "{}({})".format(self.predicate, ", ".join([str(x) for x in self.literals]))

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash((self.predicate,) + tuple(self.literals))

    def __lt__(self, other):
        return str(self) < str(other)

    def __init__(self, name: str, *literals):
        if not literals:
            self.predicate = self._predicate(name)
            self.literals = self._literals(name)
        else:
            self.predicate = name
            self.literals = list(literals)

    @property
    def all(self):
        return [self.predicate] + self.literals

    @staticmethod
    def _predicate(term: str):
        match = re.search(r"(.*)\(", term)
        if match is not None:
            return match.group(1)
        else:
            return term

    @staticmethod
    def _literals(term: str):
        match = re.search(r".*\((.*)\)", term)
        if match is not None:
            literals = match.group(1)
            return [x.strip() for x in literals.split(",")]
        else:
            return []

    def count_variables(self):
        count = 0
        for value in self.literals:
            if isinstance(value, Variable):
                count += 1
        return count

    def pin(self, variables, parameters):
        y = dict(zip(variables, parameters))
        return Term(self.predicate, *[y[x] if x in y else x for x in self.literals])


class Rule(object):
    def __init__(self, name, parameters: List[Variable], body: Expression):
        self.name = name
        self.parameters = parameters
        self.body = body

    def __str__(self):
        return "{}({}) => {}".format(self.name, ", ".join([str(x) for x in self.parameters]), self.body)

    def __repr__(self):
        return str(self)


class Action(object):
    def __init__(self, name, parameters, score, requirements, add, delete, deterministic, significant_parameters,
                 bindings, step: Step):
        self.name = name
        self.parameters = parameters
        self.score = score
        self.requirements = requirements
        self.add = add
        self.delete = delete
        self.deterministic = deterministic
        self.significant_parameters = significant_parameters
        self.bindings = bindings
        self.step = step
        self.non_params = set()

        # update non_params
        for idx, val in enumerate(self.parameters):
            for cond in self.add + self.delete:
                if val in cond.literals:
                    self.non_params.add(idx)

    def build_post_conditions(self, *actions_args):
        assert_actions = [("assert", x.pin(self.parameters, actions_args)) for x in self.add]
        retract_actions = [("retract", x.pin(self.parameters, actions_args)) for x in self.delete]
        return assert_actions + retract_actions

    def build_database_dict(self):
        return {'name': self.name,
                'parameters': [str(x) for x in self.parameters],
                'score': self.score,
                'requirement_terms': [term_to_db(x) for x in self.requirements if isinstance(x, Term)],
                'requirement_comparisons': [comp_to_db(x) for x in self.requirements if isinstance(x, Comparison)],
                'add': [term_to_db(x) for x in self.add],
                'remove': [term_to_db(x) for x in self.delete],
                'deterministic': self.deterministic,
                'significant_parameters': self.significant_parameters,
                'bindings': {k: str(v) for k, v in self.bindings.items()}}

    @staticmethod
    def _compress(expr_list: Iterable[Expression]):
        body = None
        for t in expr_list:
            if not body:
                body = t
            else:
                body = Comparison('&', t, body)
        return body

    def get_rule(self):
        return Rule(self.name, self.parameters, self._compress(reversed(self.requirements)))

    def get_meaningful_rules(self):
        # deterministic actions are only meaningful if their postconditions do not already exist
        type_body = defaultdict(list)
        type_params = defaultdict(list)
        for postcond in self.add:
            for literal in postcond.literals[1:]:
                if isinstance(literal, Variable):
                    type_params[postcond.literals[0]].append(literal)

            if isinstance(postcond, Term) and postcond.predicate not in ('has_property', 'has_member',
                                                                         'defines_property'):
                type_body[postcond.literals[0]].append(postcond)
            elif isinstance(postcond, Term) and postcond.predicate in ('has_property', 'has_member'):
                if isinstance(postcond.literals[0], Variable):
                    type_body[postcond.literals[0]].append(postcond)
                else:
                    raise CaseException
            elif isinstance(postcond, Term) and postcond.predicate == 'defines_property':
                pass
            else:
                raise CaseException

        # group all postconds by object
        rules = []
        counter = 0
        for key, collected in type_body.items():
            params = type_params[key]
            body = self._compress(collected)
            rules.append(Rule("{}_meaning{}".format(self.name, counter), list(params), body))
            counter += 1

        return rules

    @staticmethod
    def load_from_database(d: db.CodedStep, step):
        return Action(name=d.name,
                      parameters=[Variable(x) for x in d.parameters],
                      score=d.score,
                      requirements=[db_to_term(x) for x in d.requirement_terms] + [db_to_comp(x) for x in d.requirement_comparisons],
                      add=[db_to_term(x) for x in d.add],
                      delete=[db_to_term(x) for x in d.remove],
                      deterministic=d.deterministic,
                      significant_parameters=d.significant_parameters,
                      bindings={k: Variable(v) for k, v in d.bindings.items()},
                      step=step)


class LogicContext(object):
    def define_rule(self, rule: Rule) -> None:
        raise NotImplementedError

    def assert_fact(self, fact: Term) -> None:
        raise NotImplementedError

    def retract_fact(self, fact: Term) -> None:
        raise NotImplementedError

    def retract_all_facts(self) -> None:
        raise NotImplementedError

    def query(self, expression: Expression) -> Set[Tuple[Union[str, int, bool], ...]]:
        raise NotImplementedError

    def define_predicate(self, name: str, arity: int) -> None:
        raise NotImplementedError

    def get_facts(self) -> List[Term]:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


def object_to_db(p):
    if isinstance(p, str):
        return 'str', p
    elif isinstance(p, bool):
        return 'bool', str(p)
    elif isinstance(p, Variable):
        return 'var', str(p)
    else:
        raise CaseException


def db_to_object(typ, obj):
    if typ == 'str':
        return obj
    elif typ == 'bool':
        return obj == 'True'
    elif typ == 'var':
        return Variable(obj)
    else:
        raise CaseException


def term_to_db(t: Term) -> db.Term:
    literals = []
    for p in t.literals:
        typ, str_p = object_to_db(p)
        literals.extend([typ, str_p])

    return db.Term(predicate=t.predicate, literals=literals)


def db_to_term(t: db.Term) -> Term:
    trans_literals = []
    for i in range(0, len(t.literals), 2):
        trans_literals.append(db_to_object(t.literals[i], t.literals[i + 1]))
    return Term(t.predicate, *trans_literals)


def comp_to_db(c: Comparison):
    return db.Comparison(obj1=object_to_db(c.obj1), comp=c.comparator, obj2=object_to_db(c.obj2))


def db_to_comp(c: db.Comparison):
    return Comparison(obj1=db_to_object(*c.obj1), comparator=c.comp, obj2=db_to_object(*c.obj2))


# Makes an action object from a step and produces bindings from the step's parameters to the action's parameters
def convert_to_action(step: Step, unique_count) -> Action:
    action_params = []
    action_preconditions = []
    action_positive_postconditions = []
    action_negative_postconditions = []
    hints = {k: v for k, v in step.hints}
    preconditions = [(x, y) if x not in hints else (x, hints[x]) for x, y in step.preconditions]
    postconditions = [(x, y) if x not in hints else (x, hints[x]) for x, y in step.postconditions]
    bindings = {}

    def get_bind_name(object_name, property_name):
        if property_name == "":
            return "{}".format(object_name).lower()
        else:
            return "{}.{}".format(object_name, property_name).lower()

    def bind_conditions(object_property_cond_tuples, name=None):
        bound = None
        for object_name, property_name, cond_list in object_property_cond_tuples:
            bind_name = get_bind_name(object_name, property_name)
            if bind_name in bindings:
                bound = bindings[bind_name]
        for object_name, property_name, cond_list in object_property_cond_tuples:
            bind_name = get_bind_name(object_name, property_name)
            if bind_name not in bindings:
                if bound is None:
                    if name is None:
                        name = property_name
                    bound = Variable(name.upper())
                    if bound in bindings.values():
                        bound = Variable("{}_{}".format(name, unique_count()).upper())
                bindings[bind_name] = bound
                if property_name != "":
                    object_bound = bind_object_name(object_name)
                    cond_list.append(Term("has_property", object_bound, property_name, bound))
        return bound

    def bind_value(object_name: str, property_name: str, value, cond_list):
        bind_name = get_bind_name(object_name, property_name)
        if bind_name in bindings:
            raise Exception("Value already bound")
        bindings[bind_name] = value
        object_bound = bind_object_name(object_name)
        cond_list.append(Term("has_property", object_bound, property_name, bindings[bind_name]))

    def bind_object(object_name, object_type, cond_list, name=None):
        bound = bind_object_name(object_name, name=name)
        cond_list.append(Term(object_type.lower(), bound))

    def bind_object_name(object_name, name=None):
        bind_name = get_bind_name(object_name, "")
        bound = name
        if bind_name not in bindings:
            if bound is None:
                bound = Variable(object_name.upper())
            bindings[bind_name] = bound
        else:
            bound = bindings[bind_name]
        return bound

    def lookup_binding(object_name, property_name):
        bind_name = get_bind_name(object_name, property_name)
        return bindings[bind_name]

    def bind_inequality(object_name1, property_name1, object_name2, property_name2, cond_list):
        bound1 = bind_conditions([(object_name1, property_name1, cond_list)])
        bound2 = bind_conditions([(object_name2, property_name2, cond_list)])
        cond_list.append(Comparison("!=", bound1, bound2))

    def defines_property(property, cond_list):
        props = property.split(".")

        if len(props) == 2:
            cond_list.append(Term("defines_property", lookup_binding(props[0], ''), props[1]))
        else:
            raise Exception("Unhandled property length")

    def generate_conditions(condition, cond_list):
        if isinstance(condition[1], type):
            bind_object(condition[0], condition[1].__name__, cond_list)
            return

        parameter = condition[0].upper()
        requirements = condition[1].obj

        if type(requirements) == dict:
            # Declare the variable.
            bind_object(condition[0], condition[1].__class__.__name__, cond_list)
            for key, value in requirements.items():
                if key == "$in":
                    # So, we must have something like { "$in" : {dict}}
                    if type(value) == dict:
                        # OPCredential({'$in': {'user_id': OPVar("host.local_admins")}})),
                        for field, lookup in value.items():
                            # First, we have to add has_property(PARAMETER, field, FIELD_RANDOM)
                            assert type(lookup) == OPVar
                            opvar_split = lookup.obj.split(".")
                            bound = bind_conditions([(parameter.upper(), field.lower(), cond_list)])
                            cond_list.append(
                                Term("has_member", lookup_binding(opvar_split[0], ''), opvar_split[1].lower(),
                                     bound))
                    elif type(value) == OPVar:
                        opvar_split = value.obj.split(".")
                        bound = lookup_binding(parameter, "")
                        cond_list.append(
                            Term("has_member", lookup_binding(opvar_split[0], ''), opvar_split[1].lower(), bound))
                    else:
                        raise Exception("Unexpected type")
                else:
                    if type(value) == OPVar:
                        # OPVar statements are usually "property : OPVar(<value>.<prop>)
                        opvar_split = value.obj.split(".")
                        assert 1 <= len(opvar_split) <= 2
                        conds = [(parameter, key, cond_list)]
                        # bind the opvar lookup to a precondition if it is a precondition, else a postcondition
                        if opvar_split[0] in [x for x, y in preconditions]:
                            cond = action_preconditions
                        else:
                            cond = action_positive_postconditions

                        if len(opvar_split) == 2:
                            conds.append((opvar_split[0], opvar_split[1], cond))
                        else:
                            conds.append((opvar_split[0], "", cond))
                        bind_conditions(conds, name=key)
                    elif type(value) == str or type(value) == bool:
                        bind_value(parameter, key, value, cond_list)
                    else:
                        raise Exception("Warning unhandled value type")
        elif type(requirements) == OPVar:
            opvar_split = requirements.obj.split(".")
            assert len(opvar_split) == 2
            # bind the opvar lookup to a precondition if it is a precondition, else a postcondition
            if opvar_split[0] in [x for x, y in preconditions]:
                cond = action_preconditions
            else:
                cond = action_positive_postconditions
            bound = bind_conditions([(opvar_split[0], opvar_split[1], cond)])
            # Declare the variable.
            bind_object(condition[0], condition[1].__class__.__name__, cond_list, name=bound)
        else:
            raise Exception("Unexpected type")

    for precondition in preconditions:
        generate_conditions(precondition, action_preconditions)

    for postcondition in postconditions:
        generate_conditions(postcondition, action_positive_postconditions)

    for not_equal in step.not_equal:
        not_equal0 = not_equal[0].split('.')
        not_equal1 = not_equal[1].split('.')
        if len(not_equal0) == 1:
            not_equal0.append("")
        if len(not_equal1) == 1:
            not_equal1.append("")

        bind_inequality(*not_equal0, *not_equal1, action_preconditions)

    for property in step.preproperties:
        props = property.split('.')
        prop_name = props.pop(0)
        while props:
            property1 = props.pop(0)
            bound = bind_conditions([(prop_name, property1, action_preconditions)])
            prop_name += ".{}".format(property1)

    for property in step.postproperties:
        defines_property(property, action_positive_postconditions)

    for precondition in action_preconditions:
        if isinstance(precondition, Term):
            for literal in precondition.literals:
                if isinstance(literal, Variable) and literal not in action_params:
                    action_params.append(literal)

    sig_params = []
    for item in step.significant_parameters:
        props = item.split('.')
        prop_name = props.pop(0)
        if len(props) != 0:
            raise Exception("significant parameters must not have properties")

        out_param = lookup_binding(prop_name, "")
        sig_params.append(action_params.index(out_param))

    precond_names = [x for x, y in step.preconditions]
    bound_variables = {x.split('.')[0]: y for x, y in bindings.items() if
                       len(x.split('.')) == 1 and x.split('.')[0] in precond_names}
    return Action(step.__name__, action_params, step.value, action_preconditions, action_positive_postconditions,
                  action_negative_postconditions, step.deterministic, sig_params, bound_variables, step)


def cddl_to_old_specification(cddl, schema):
    """
    Takes in cddl and returns an old format action with pre/post conditions and significant parameters, deterministic,
    etc.
    Args:
        cddl:

    Returns:

    """
    preconditions = []
    postconditions = []
    preproperties = []
    postproperties = []
    deterministic = None
    not_equal = []
    hints = []
    significant_parameters = []
    ast = get_ast(cddl, schema)

    return preconditions, postconditions, preproperties, postproperties, deterministic, not_equal, hints, \
           significant_parameters


def remove_or_comparisons(expr: Expression) -> List[Expression]:
    """Removes 'OR' operators from the expression by converting the expression to a list of conjunctions, which could
    together be disjuncted to get an expression that is logically equivalent to the input"""
    if isinstance(expr, Comparison):
        if expr.comparator == "|":
            return remove_or_comparisons(expr.obj1) + remove_or_comparisons(expr.obj2)
        else:
            return [Comparison(expr.comparator, r1, r2) for r1, r2 in product(remove_or_comparisons(expr.obj1), remove_or_comparisons(expr.obj2))]
    else:
        return [expr]
