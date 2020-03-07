from app.objects.c_ability import Ability
from app.utility.base_world import BaseWorld
from tests.base.test_base import TestBase


class TestRestSvc(TestBase):

    def setUp(self):
        self.initialize()
        BaseWorld.apply_config({'app.contact.http': '0.0.0.0', 'plugins': ['sandcat', 'stockpile']})
        self.run_async(self.data_svc.store(
            Ability(ability_id='123', test=BaseWorld.encode_string('curl #{app.contact.http}')))
        )

    def test_update_config(self):
        # check that an ability reflects the value in app. property
        pre_ability = self.run_async(self.data_svc.locate('abilities', dict(ability_id='123')))
        self.assertEqual('0.0.0.0', BaseWorld.get_config('app.contact.http'))
        self.assertEqual('curl 0.0.0.0', BaseWorld.decode_bytes(pre_ability[0].test))

        # update property
        self.run_async(self.rest_svc.update_config(data=dict(prop='app.contact.http', value='127.0.0.1')))

        # verify ability reflects new value
        post_ability = self.run_async(self.data_svc.locate('abilities', dict(ability_id='123')))
        self.assertEqual('127.0.0.1', BaseWorld.get_config('app.contact.http'))
        self.assertEqual('curl 127.0.0.1', BaseWorld.decode_bytes(post_ability[0].test))

    def test_update_config_plugin(self):
        # update plugin property
        self.assertEqual(['sandcat', 'stockpile'], BaseWorld.get_config('plugins'))
        self.run_async(self.rest_svc.update_config(data=dict(prop='plugin', value='ssl')))
        self.assertEqual(['sandcat', 'stockpile', 'ssl'], BaseWorld.get_config('plugins'))
