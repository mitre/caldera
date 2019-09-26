import unittest

import app.parsers.standard as parsers


class TestRegexParser(unittest.TestCase):
    def test_regex(self):
        test_blob = """
        127.0.0.1 text
        other text 0.0.0.0
        """
        parser_info = {
            'ability': 82,
            'name': 'regex',
            'property': 'test.sample.ip',
            'script': '[0-9]+(?:\.[0-9]+){3}'
        }

        matched_facts = parsers.regex(parser=parser_info, blob=test_blob, log=None)
        self.assertEqual(matched_facts[0]['fact'], parser_info['property'])

        fact_values = [fact['value'] for fact in matched_facts]
        self.assertEqual(fact_values, ['127.0.0.1', '0.0.0.0'])


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


class TestLineParser(unittest.TestCase):
    def test_line(self):
        test_blob = "/path/to/dir"
        parser_info = {'ability': 1, 'name': 'line', 'property': 'host.dir.staged', 'script': ''}

        matched_facts = parsers.line(parser=parser_info, blob=test_blob, log=None)
        self.assertEqual(matched_facts[0]['fact'], parser_info['property'])
        self.assertEqual(matched_facts[0]['value'], test_blob)

    def test_multi_line(self):
        test_blob = """
        /path/to/dir

        /path/to/dir2
        /path/to/dir3
        """
        parser_info = {'ability': 1, 'name': 'line', 'property': 'host.dir.staged', 'script': ''}

        matched_facts = parsers.line(parser=parser_info, blob=test_blob, log=None)
        self.assertEquals(len(matched_facts), 3)
        self.assertEqual(matched_facts[0]['fact'], parser_info['property'])

        fact_values = [fact['value'] for fact in matched_facts]
        self.assertEqual(fact_values, ['/path/to/dir', '/path/to/dir2', '/path/to/dir3'])
