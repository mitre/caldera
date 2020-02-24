import unittest

from app.learning.p_ip import Parser as p_ip
from app.learning.p_path import Parser as p_path
from tests.base.test_base import TestBase


class TestFile(TestBase):

    @unittest.SkipTest
    def test_ip(self):
        parser = p_ip()
        results = list(parser.parse('this ip 10.1.2.3 and 5.3.4.6 will be parsed, but 0.0.0.0, 1.2.3 and 127.0.0.1 will not'))
        self.assertEqual(2, len(results))
        self.assertTrue('10.1.2.3' in [r.value for r in results])
        self.assertTrue('5.3.4.6' in [r.value for r in results])

    @unittest.SkipTest
    def test_path(self):
        parser = p_path()
        results = list(parser.parse('first /some/file/path/one.txt for linux and C:\Some\Windows.blah and even C:\\\Public Here\\\Stuff.exe and'
                                    '/Users/tricky/rsc.io_quote_v1.5.1.txt'))
        self.assertEqual(4, len(results))
        self.assertTrue('/some/file/path/one.txt' in [r.value for r in results])
        self.assertTrue('/Users/tricky/rsc.io_quote_v1.5.1.txt' in [r.value for r in results])
        self.assertTrue('C:\Some\Windows.blah' in [r.value for r in results])
        self.assertTrue('C:\\\Public Here\\\Stuff.exe' in [r.value for r in results])
