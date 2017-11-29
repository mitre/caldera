from unittest import TestCase
import json
from caldera.tests.test_world import schema_json
from caldera.app.operation.operation_steps import all_steps
from caldera.app.cddl.build_ast import get_ast
from caldera.app.logic.logic import cddl_to_old_specification


class TestGetAst(TestCase):
    def test_get_ast(self):
        for step in all_steps:
            if step.cddl:
                get_ast(step.cddl, json.loads(schema_json))

    def test_cddl_to_old_format(self):
        for step in all_steps:
            if step.cddl:
                preconditions, postconditions, preproperties, postproperties, deterministic, not_equal, hints, \
                    significant_parameters = cddl_to_old_specification(step.cddl,  json.loads(schema_json))

                self.assertEqual(preconditions, step.preconditions)
                self.assertEqual(postconditions, step.postconditions)
                self.assertEqual(preproperties, step.preproperties)
                self.assertEqual(postproperties, step.postproperties)
                self.assertEqual(deterministic, step.deterministic)
                self.assertEqual(not_equal, step.not_equal)
                self.assertEqual(hints, step.hints)
                self.assertEqual(significant_parameters, step.significant_parameters)
