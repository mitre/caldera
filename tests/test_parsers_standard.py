import unittest

import app.parsers.standard as parsers


class TestJSONParser(unittest.TestCase):
    def test_json_value(self):
        test_blob = """    
        {
            "debug": "on",
            "test": "test"
        }
        """
        parser_info = {'ability': 82, 'name': 'json', 'property': 'host.user.name', 'script': 'debug'}

        matched_facts = parsers.json(parser=parser_info, blob=test_blob, log=None)
        self.assertEqual(matched_facts[0]['fact'], parser_info['property'])
        self.assertEqual(matched_facts[0]['value'], 'on')

    def test_json_list(self):
        test_blob = """    
        {
            "status": "up",
            "months": ["jun", "jul", "aug"]
        }
        """
        parser_info = {'ability': 82, 'name': 'json', 'property': 'summer.months', 'script': 'months'}

        matched_facts = parsers.json(parser=parser_info, blob=test_blob, log=None)
        self.assertEqual(matched_facts[0]['fact'], parser_info['property'])
        self.assertEqual(matched_facts[0]['value'], ['jun', 'jul', 'aug'])

