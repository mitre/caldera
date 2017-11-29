import unittest
from caldera.app.logic.logic import Term, convert_to_action
from caldera.app.operation.operation_steps import all_steps
import itertools


class TestActionConversion(unittest.TestCase):
    #   We want to detect situations such as this:
    #       +  has_property(user_id, CREDENTIAL_G, USER_ID_18)
    #       +  has_property(user_id, CREDENTIAL_G, USER_ID_19)
    i = 0

    @classmethod
    def unique_count(cls):
        cls.i += 1
        return cls.i

    def test_duplicate_conditions(self):
        for step in all_steps:
            new_action = convert_to_action(step, self.unique_count)
            terms_only = [x for x in new_action.requirements + new_action.add if isinstance(x, Term)]
            for statement, other_statement in itertools.combinations(terms_only, 2):
                #   We only care about has_property statements
                if statement.predicate == "has_property" and other_statement.predicate == "has_property" and \
                        other_statement.literals[0] == statement.literals[0] and \
                        other_statement.literals[1] == statement.literals[1]:
                    self.assertEqual(other_statement.literals[2], statement.literals[2])

    # We want to detect situations where an object is defined in the post-conditions but a has_property predicate
    # in the preconditions references a field of that object. This should never happen
    def test_object_defined_in_post_conditions(self):
        for step in all_steps:
            new_action = convert_to_action(step, self.unique_count)
            objects_in_post = []
            for term in new_action.add:
                if isinstance(term, Term) and len(term.literals) == 1:
                    objects_in_post.append(term.literals[0])
            for term in new_action.requirements:
                if isinstance(term, Term) and term.predicate == "has_property":
                    self.assertNotIn(term.literals[1], objects_in_post)
