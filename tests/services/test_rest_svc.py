import pytest

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.utility.base_world import BaseWorld


@pytest.fixture
def setup_rest_svc_test(loop, data_svc):
    BaseWorld.apply_config(name='default', config={'app.contact.http': '0.0.0.0', 'plugins': ['sandcat', 'stockpile']})
    loop.run_until_complete(data_svc.store(
        Ability(ability_id='123', test=BaseWorld.encode_string('curl #{app.contact.http}'), variations=[]))
    )


@pytest.mark.usefixtures(
    "setup_rest_svc_test"
)
class TestRestSvc:

    def test_update_config(self, loop, data_svc, rest_svc):
        internal_rest_svc = rest_svc(loop)
        # check that an ability reflects the value in app. property
        pre_ability = loop.run_until_complete(data_svc.locate('abilities', dict(ability_id='123')))
        assert '0.0.0.0' == BaseWorld.get_config('app.contact.http')
        assert 'curl 0.0.0.0' == BaseWorld.decode_bytes(pre_ability[0].test)

        # update property
        loop.run_until_complete(internal_rest_svc.update_config(data=dict(prop='app.contact.http', value='127.0.0.1')))

        # verify ability reflects new value
        post_ability = loop.run_until_complete(data_svc.locate('abilities', dict(ability_id='123')))
        assert '127.0.0.1' == BaseWorld.get_config('app.contact.http')
        assert 'curl 127.0.0.1' == BaseWorld.decode_bytes(post_ability[0].test)

    def test_update_config_plugin(self, loop, rest_svc):
        internal_rest_svc = rest_svc(loop)
        # update plugin property
        assert ['sandcat', 'stockpile'] == BaseWorld.get_config('plugins')
        loop.run_until_complete(internal_rest_svc.update_config(data=dict(prop='plugin', value='ssl')))
        assert ['sandcat', 'stockpile', 'ssl'] == BaseWorld.get_config('plugins')

    def test_delete_ability(self):
        self.assertEqual('Delete action completed', self.run_async(
            self.rest_svc.delete_ability(data=dict(ability_id='123'))))

    def test_delete_adversary(self):
        data = """
---
- id: 123
  name: test
  description: test
  phases:
        """
        with open('data/adversaries/123.yml', 'w') as f:
            f.write(data)
        self.assertEqual('Delete action completed', self.run_async(
            self.rest_svc.delete_adversary(data=dict(adversary_id='123'))))
