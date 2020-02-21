import unittest

from app.objects.secondclass.c_fact import Fact


class TestFact(unittest.TestCase):
    def test_escaped_cmd(self):
        test_fact = Fact('test', 'test value| &')
        self.assertEqual(test_fact.escaped('cmd'), 'test^ value^|^ ^&')
        self.assertNotEqual(test_fact.escaped('cmd'), 'test value| &')

    def test_escaped_sh(self):
        test_fact = Fact('test', 'test value| &')
        self.assertEqual(test_fact.escaped('sh'), 'test\ value\|\ \&')
        self.assertNotEqual(test_fact.escaped('sh'), 'test value| &')

    def test_escaped_psh(self):
        test_fact = Fact('test', 'test value| &')
        self.assertEqual(test_fact.escaped('psh'), 'test` value`|` `&')
        self.assertNotEqual(test_fact.escaped('psh'), 'test value| &')
