from pyDatalog import pyDatalog, pyParser
from .logic import Variable, Comparison, Term, Expression, LogicContext, Rule, Unary, remove_or_comparisons
import collections


class DatalogContext(LogicContext):
    def __init__(self):
        self.terms = {}
        self.facts = []

    def _define_term(self, term):
        predicate = self.terms.get(term, None)
        if not predicate:
            predicate = pyParser.Term(term)
            self.terms[term] = predicate
        return predicate

    def define_rule(self, rule: Rule):
        # noinspection PyUnusedLocal
        variable_map = collections.defaultdict(lambda: pyDatalog.Variable())

        exec_str = 'self._define_term(rule.name)(*[variable_map[x.name] for x in rule.parameters]) <= '

        for rule_expr in remove_or_comparisons(rule.body):
            exec(exec_str + self._build_query_str(rule_expr, "rule_expr"), locals(), globals())

    def assert_fact(self, fact: Term):
        self.facts.append(fact)
        predicate = self._define_term(fact.predicate)
        # noinspection PyStatementEffect
        + predicate(*fact.literals)

    def retract_fact(self, fact: Term):
        self.facts.remove(fact)
        predicate = self._define_term(fact.predicate)
        # noinspection PyStatementEffect
        - predicate(*fact.literals)

    def retract_all_facts(self):
        while self.facts:
            self.retract_fact(self.facts[0])

    def _create_query(self, pred: str, *parameters):
        variable_map = collections.defaultdict(pyDatalog.Variable)
        query = self._define_term(pred)(*[variable_map[x.name] if isinstance(x, Variable) else x for x in parameters])
        return query

    def _build_query_str(self, expr: Expression, base_str: str):
        if isinstance(expr, Term):
            literals = []
            for idx, x in enumerate(expr.literals):
                if isinstance(x, Variable):
                    literals.append("variable_map['{}']".format(x.name))
                else:
                    literals.append('{}.literals[{}]'.format(base_str, idx))
            return "self._define_term('{}')({})".format(expr.predicate, ', '.join(literals))
        elif isinstance(expr, Comparison):
            query1 = self._build_query_str(expr.obj1, base_str + ".obj1")
            query2 = self._build_query_str(expr.obj2, base_str + ".obj2")
            if expr.comparator == '&':
                return "{} {} {}".format(query1, expr.comparator, query2)
            elif expr.comparator == '|':
                return "({} or {})".format(query1, query2)
            else:
                return "({} {} {})".format(query1, expr.comparator, query2)
        elif isinstance(expr, Unary):
            query1 = self._build_query_str(expr.obj1, base_str + ".obj1")
            return "{}({})".format(expr.operator, query1)
        elif isinstance(expr, Variable):
            return "variable_map['{}']".format(expr.name)
        raise Exception("Unrecognized expression: {}".format(expr))

    def _query_without_ask(self, expression: Expression):
        if isinstance(expression, Term):
            return self._create_query(expression.predicate, *expression.literals)
        elif isinstance(expression, Comparison):
            variable_map = collections.defaultdict(pyDatalog.Variable)
            exec_blob = self._build_query_str(expression, "expression")
            local_dict = locals()
            exec('retval = ' + exec_blob, {**globals(), **local_dict}, local_dict)
            return local_dict["retval"]
        raise Exception("Unrecognized expression: {}".format(expression))

    def query(self, expression: Expression):
        query = self._query_without_ask(expression)
        try:
            answers = query.ask()
        except AttributeError as ae:
            if len(ae.args) > 0 and ae.args[0].startswith('Predicate without definition (or error in resolver):'):
                raise
            return set()

        # hacky, but we have to filter out the dummy predicate
        answers = set(filter(lambda x: '__dummy__' not in x, answers))
        return answers

    def define_predicate(self, name: str, arity: int):
        # this is hacky but avoids an annoying pydatalog behavior when dealing with predicates that aren't defined
        # Note this (purposely) doesn't get stored in self.facts so it isn't retract in retract_all_facts
        self.assert_fact(Term(name, *['__dummy__']*arity))

    def get_facts(self):
        return self.facts

    def close(self):
        pyDatalog.clear()
