import unittest
from caldera.app.logic.logic import Variable, Comparison, Term, Rule, Unary
from caldera.app.util import relative_path
from caldera.app.logic.pydatalog_logic import DatalogContext


class TestLogic(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        with open(relative_path(__file__, '10_host_dataset.txt')) as f:
            dataset = f.readlines()

        self.dataset = []
        for fact in sorted(dataset, key=lambda x: x.count(',')):
            term = Term(fact.strip())
            term.literals = list(True if x == "True" else False if x == "False" else x for x in term.literals)
            self.dataset.append(term)

        super().__init__(*args, **kwargs)

    def test_simple_datalog(self):
        context = DatalogContext()
        self._test_simple(context)
        context.close()

    def test_complex_datalog(self):
        context = DatalogContext()
        self._test_complex(context)
        context.close()

    def test_str_in_rule_datalog(self):
        context = DatalogContext()
        self._test_str_in_rule(context)
        context.close()

    def test_negation_datalog(self):
        context = DatalogContext()
        self._test_negation(context)
        context.close()

    def test_fact_retract_datalog(self):
        context = DatalogContext()
        self._test_fact_retract(context)
        context.close()

    def test_rule_retract_datalog(self):
        context = DatalogContext()
        self._test_rule_retract(context)
        context.close()

    def test_strings_datalog(self):
        context = DatalogContext()
        self._test_strings(context)
        context.close()

    def test_numbers_datalog(self):
        context = DatalogContext()
        self._test_numbers(context)
        context.close()

    def test_bool_datalog(self):
        context = DatalogContext()
        self._test_bool(context)
        context.close()

    def test_order_of_operations_datalog(self):
        context = DatalogContext()
        self._test_order_of_operations(context)
        context.close()

    def _test_simple(self, context):
        a = Variable('a')
        b = Variable('b')
        c = Variable('c')
        sibling_rule = Rule('sibling', [a, b],
                            Comparison('&',
                                       Comparison('&',
                                                  Term('father', c, a),
                                                  Term('father', c, b)),
                                       Comparison('!=', a, b)))
        context.define_rule(sibling_rule)

        context.assert_fact(Term('father(adam, cain)'))
        context.assert_fact(Term('mother(eve, cain)'))
        context.assert_fact(Term('father(adam, abel)'))
        context.assert_fact(Term('mother(eve, abel)'))

        d = Variable('d')
        e = Variable('e')
        query_result = context.query(Term("sibling", d, e))
        # find all siblings
        self.assertEqual({('cain', 'abel'), ('abel', 'cain')}, set(query_result))

    def _test_complex(self, context):
        # this code converts all of the steps in all_steps
        # Credentials(RAT, HOST) => opexec(RAT) & has_property(RAT, elevated, True) &
        # has_property(RAT, host, HOST) & ophost(HOST)
        rat = Variable('RAT')
        host = Variable('HOST')
        cred_rule = Rule('Credentials', [rat, host],
                          Comparison('&',
                                     Comparison('&',
                                                Comparison('&',
                                                           Term('opexec', rat),
                                                           Term('has_property', rat, 'host', host)),
                                                Term('has_property', rat, 'elevated', True)),
                                     Term('ophost', host)))

        context.define_rule(cred_rule)

        for fact in self.dataset:
            context.assert_fact(fact)

        query_result = context.query(Term('Credentials', rat, host))

        result = [('58e6b12f85b28c3b3628c920', '58e6b0f585b28c3b3628c904'),
                  ('58e6b9e785b28c3b3628c98a', '58e6b0f585b28c3b3628c905'),
                  ('58e6b0ad85b28c3b3628c8e9', '58e6b0a385b28c3b3628c8e5'),
                  ('58e6b14585b28c3b3628c92b', '58e6b0f585b28c3b3628c906'),
                  ('58e6b16885b28c3b3628c936', '58e6b0f585b28c3b3628c900'),
                  ('58e6b1bd85b28c3b3628c941', '58e6b0f585b28c3b3628c901'),
                  ('58e6b2b885b28c3b3628c953', '58e6b0f585b28c3b3628c8fe'),
                  ('58e6b6cf85b28c3b3628c97f', '58e6b0f585b28c3b3628c8ff'),
                  ('58e6b3d085b28c3b3628c962', '58e6b0f585b28c3b3628c903'),
                  ('58e6b24685b28c3b3628c94b', '58e6b0f585b28c3b3628c902')]

        self.assertEqual(set(query_result), set(result))

    def _test_str_in_rule(self, context):
        rat = Variable('RAT')
        host = Variable('HOST')
        cred_rule = Rule('HostsWithRat', [rat, host],
                          Comparison('&',
                                     Comparison('&',
                                                Term('opexec', rat),
                                                Term('has_property', rat, 'host', host)),
                                     Term('ophost', host)))

        context.define_rule(cred_rule)

        for fact in self.dataset:
            context.assert_fact(fact)

        query_result = context.query(Term('HostsWithRat', rat, host))

        result = [('58e6b12f85b28c3b3628c920', '58e6b0f585b28c3b3628c904'),
                  ('58e6b9e785b28c3b3628c98a', '58e6b0f585b28c3b3628c905'),
                  ('58e6b0ad85b28c3b3628c8e9', '58e6b0a385b28c3b3628c8e5'),
                  ('58e6b14585b28c3b3628c92b', '58e6b0f585b28c3b3628c906'),
                  ('58e6b16885b28c3b3628c936', '58e6b0f585b28c3b3628c900'),
                  ('58e6b1bd85b28c3b3628c941', '58e6b0f585b28c3b3628c901'),
                  ('58e6b2b885b28c3b3628c953', '58e6b0f585b28c3b3628c8fe'),
                  ('58e6b6cf85b28c3b3628c97f', '58e6b0f585b28c3b3628c8ff'),
                  ('58e6b3d085b28c3b3628c962', '58e6b0f585b28c3b3628c903'),
                  ('58e6b24685b28c3b3628c94b', '58e6b0f585b28c3b3628c902')]

        self.assertEqual(set(query_result), set(result))

    def _test_negation(self, context):
        # good_for_skipping(thing) => small(thing) & hard(thing) & ~bumpy(thing)
        thing = Variable('THING')
        skip_rule = Rule('good_for_skipping', [thing],
                         Comparison('&',
                                    Comparison('&', Term('small', thing), Term('hard', thing)),
                                    Unary('~', Term('bumpy', thing))))

        context.define_rule(skip_rule)

        context.assert_fact(Term('small(paper_towel)'))
        context.assert_fact(Term('big(elephant)'))
        context.assert_fact(Term('hard(elephant)'))
        context.assert_fact(Term('small(pebble)'))
        context.assert_fact(Term('hard(pebble)'))
        context.assert_fact(Term('small(rock)'))
        context.assert_fact(Term('hard(rock)'))
        context.assert_fact(Term('bumpy(rock)'))

        query_result = context.query(Term('good_for_skipping', thing))

        result = [('pebble',)]

        self.assertEqual(set(query_result), set(result))

    def _test_fact_retract(self, context):
        thing = Variable('THING')
        t1 = 'small(paper_towel)'
        t2 = 'small(pebble)'
        context.assert_fact(Term(t1))
        context.assert_fact(Term(t2))

        query_result = context.query(Term('small', thing))
        self.assertEqual({('paper_towel',), ('pebble',)}, set(query_result))

        context.retract_fact(Term(t1))
        query_result = context.query(Term('small', thing))
        self.assertEqual({('pebble',)}, set(query_result))

    def _test_rule_retract(self, context):
        # good_for_skipping(thing) => small(thing) & hard(thing) & ~bumpy(thing)
        thing = Variable('THING')
        skip_rule = Rule('good_for_skipping', [thing], Term('small', thing))

        context.define_rule(skip_rule)

        t1 = Term('small(paper_towel)')
        context.assert_fact(t1)

        query_result = context.query(Term('good_for_skipping', thing))
        self.assertEqual({('paper_towel',)}, set(query_result))

        context.retract_fact(t1)
        query_result = context.query(Term('good_for_skipping', thing))
        self.assertEqual(set(), set(query_result))

    def _test_strings(self, context):
        # good_for_skipping(thing) => small(thing) & hard(thing) & ~bumpy(thing)
        thing = Variable('THING')
        skip_rule = Rule('good_for_skipping', [thing], Term('small', thing))

        context.define_rule(skip_rule)

        t1 = Term('small', 'paper towel')
        context.assert_fact(t1)

        query_result = context.query(Term('good_for_skipping', thing))
        self.assertEqual({('paper towel',)}, set(query_result))

    def _test_numbers(self, context):
        # good_for_skipping(thing) => small(thing) & hard(thing) & ~bumpy(thing)
        thing = Variable('THING')
        skip_rule = Rule('good_for_skipping', [thing], Term('small', thing))

        context.define_rule(skip_rule)

        t1 = Term('small', 9)
        context.assert_fact(t1)

        query_result = context.query(Term('good_for_skipping', thing))
        self.assertEqual({(9,)}, set(query_result))

    def _test_bool(self, context):
        # good_for_skipping(thing) => small(thing) & hard(thing) & ~bumpy(thing)
        thing = Variable('THING')
        skip_rule = Rule('good_for_skipping', [thing], Term('small', thing))

        context.define_rule(skip_rule)

        t1 = Term('small', True)
        context.assert_fact(t1)

        query_result = context.query(Term('good_for_skipping', thing))
        self.assertEqual({(True,)}, set(query_result))

    def _test_order_of_operations(self, context):
        # test_oop(A) => (one(A) | two(A)) & (three(A) | four(A))
        context.define_predicate('one', 1)
        context.define_predicate('two', 1)
        context.define_predicate('three', 1)
        context.define_predicate('four', 1)
        a = Variable('A')
        oop_rule = Rule('test_oop', [a], Comparison('&', Comparison('|', Term('one', a), Term('two', a)),
                                                    Comparison('|', Term('three', a), Term('four', a))))

        context.define_rule(oop_rule)

        truth_table = [0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1]
        for i in range(16):
            # convert to binary
            str_repr = "{0:04b}".format(i)

            if str_repr[0] == '1':
                context.assert_fact(Term('one', True))
            if str_repr[1] == '1':
                context.assert_fact(Term('two', True))
            if str_repr[2] == '1':
                context.assert_fact(Term('three', True))
            if str_repr[3] == '1':
                context.assert_fact(Term('four', True))

            query_result = context.query(Term('test_oop', a))
            desired_result = set()
            if truth_table[i] == 1:
                desired_result = {(True,)}
            try:
                self.assertEqual(desired_result, query_result)
            except AssertionError:
                print("Failed on truth value for: {}, expected {} but got {}".format(i, desired_result, query_result))
                raise
            context.retract_all_facts()
