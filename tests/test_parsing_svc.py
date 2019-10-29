import string
import random
import base64

from asynctest.mock import MagicMock

from tests.base_service import TestBaseServiceCase
from app.service.parsing_svc import ParsingService


class TestParsingService(TestBaseServiceCase):
    def test__parse_link_result(self):
        parsing_service = ParsingService()

        data_svc = MagicMock()
        data_svc.explode = MagicMock(return_value=[])
        parsing_service.data_svc = data_svc

        parser = MagicMock()
        parser.parse = MagicMock(side_effect=Exception('something went wrong'))

        for _ in range(20):
            length = random.randint(a=10, b=100)
            test_string = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(length))
            result = dict(output=base64.b64encode(test_string.encode('utf-8')), link_id=99)
            relationships = self.run_async(parsing_service._parse_link_result(result=result, parser=parser))
            self.assertEqual(len(relationships), 0)
