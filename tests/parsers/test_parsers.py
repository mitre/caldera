from app.learning.p_ip import Parser as p_ip
from app.learning.p_path import Parser as p_path


class TestFile:

    def test_ip(self):
        parser = p_ip()
        results = list(parser.parse('this ip 10.1.2.3 and 5.3.4.6 will be parsed, but 0.0.0.0, 1.2.3 and 127.0.0.1 will not'))
        assert len(results) == 2
        assert '10.1.2.3' in [r.value for r in results]
        assert '5.3.4.6' in [r.value for r in results]

    def test_path(self):
        parser = p_path()
        results = list(parser.parse('first /some/file/path/one.txt for linux and '
                                    '/Users/tricky/rsc.io_quote_v1.5.1.txt'))
        assert len(results) == 2
        assert '/some/file/path/one.txt' in [r.value for r in results]
        assert '/Users/tricky/rsc.io_quote_v1.5.1.txt' in [r.value for r in results]
