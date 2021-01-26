from unittest.mock import MagicMock

from app.objects.c_operation import Operation
from app.objects.secondclass.c_link import Link


class TestOperation:

    def test_ran_ability_id(self, ability, adversary):
        op = Operation(name='test', agents=[], adversary=adversary)
        mock_link = MagicMock(spec=Link, ability=ability(ability_id='123'), finish='2021-01-01 08:00:00')
        op.chain = [mock_link]
        assert op.ran_ability_id('123')
