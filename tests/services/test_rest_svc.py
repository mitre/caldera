import pytest

from app.objects.c_ability import Ability
from app.objects.c_agent import Agent
from app.objects.c_adversary import Adversary
from app.objects.c_obfuscator import Obfuscator
from app.objects.c_operation import Operation
from app.objects.c_planner import Planner
from app.objects.c_source import Source
from app.utility.base_world import BaseWorld


@pytest.fixture
def setup_rest_svc_test(loop, data_svc):
    BaseWorld.apply_config(name='main', config={'app.contact.http': '0.0.0.0',
                                                'plugins': ['sandcat', 'stockpile'],
                                                'crypt_salt': 'BLAH',
                                                'api_key': 'ADMIN123',
                                                'encryption_key': 'ADMIN123',
                                                'exfil_dir': '/tmp'})
    loop.run_until_complete(data_svc.store(
        Ability(ability_id='123', test=BaseWorld.encode_string('curl #{app.contact.http}'), variations=[],
                executor='psh', platform='windows'))
    )
    adversary = Adversary(adversary_id='123', name='test', description='test', atomic_ordering=[])
    loop.run_until_complete(data_svc.store(adversary))

    agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows')
    loop.run_until_complete(data_svc.store(agent))

    loop.run_until_complete(data_svc.store(
        Planner(planner_id='123', name='test', module='test', params=dict())
    ))

    source = Source(id='123', name='test', facts=[], adjustments=[])
    loop.run_until_complete(data_svc.store(source))

    loop.run_until_complete(data_svc.store(
        Operation(name='test', agents=[agent], adversary=adversary, id='123', source=source)
    ))

    loop.run_until_complete(data_svc.store(
        Obfuscator(name='plain-text',
                   description='Does no obfuscation to any command, instead running it in plain text',
                   module='plugins.stockpile.app.obfuscators.plain_text')
    ))


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

    def test_create_operation(self, loop, rest_svc, data_svc):
        want = {'name': 'Test',
                'adversary': {'description': 'an empty adversary profile', 'name': 'ad-hoc', 'adversary_id': 'ad-hoc',
                              'atomic_ordering': [], 'objective': None}, 'state': 'finished',
                'planner': {'name': 'test', 'description': None, 'module': 'test', 'stopping_conditions': [],
                            'params': {},
                            'ignore_enforcement_modules': [], 'id': '123'},
                'jitter': '2/8',
                'host_group': [
                    {'trusted': True, 'architecture': 'unknown', 'watchdog': 0, 'contact': 'unknown', 'username': 'unknown',
                     'links': [], 'sleep_max': 8, 'exe_name': 'unknown', 'executors': ['pwsh', 'psh'], 'ppid': 0,
                     'sleep_min': 2, 'server': '://None:None', 'platform': 'windows', 'host': 'unknown', 'paw': '123',
                     'pid': 0, 'display_name': 'unknown$unknown', 'group': 'red', 'location': 'unknown', 'privilege': 'User', 'proxy_receivers': {}}],
                'visibility': 50, 'autonomous': 1, 'chain': [], 'auto_close': False, 'obfuscator': 'plain-text'}
        internal_rest_svc = rest_svc(loop)
        operation = loop.run_until_complete(internal_rest_svc.create_operation(access=dict(
            access=(internal_rest_svc.Access.RED, internal_rest_svc.Access.APP)),
            data=dict(name='Test', planner='test', source='123', state='finished')))
        operation[0].pop('id')
        operation[0]['host_group'][0].pop('last_seen')
        operation[0].pop('start')
        assert want == operation[0]

    def test_delete_ability(self, loop, rest_svc, file_svc):
        internal_rest_svc = rest_svc(loop)
        response = loop.run_until_complete(internal_rest_svc.delete_ability(data=dict(ability_id='123')))
        assert 'Delete action completed' == response

    def test_delete_adversary(self, loop, rest_svc, file_svc):
        internal_rest_svc = rest_svc(loop)
        data = """
---
- id: 123
  name: test
  description: test
  atomic_ordering:
        """
        with open('data/adversaries/123.yml', 'w') as f:
            f.write(data)
        response = loop.run_until_complete(internal_rest_svc.delete_adversary(data=dict(adversary_id='123')))
        assert 'Delete action completed' == response

    def test_delete_agent(self, loop, rest_svc, file_svc):
        internal_rest_svc = rest_svc(loop)
        response = loop.run_until_complete(internal_rest_svc.delete_agent(data=dict(paw='123')))
        assert 'Delete action completed' == response

    def test_get_potential_links(self, loop, rest_svc, planning_svc, data_svc):
        internal_rest_svc = rest_svc(loop)
        internal_rest_svc.add_service('planning_svc', planning_svc)
        internal_rest_svc.add_service('data_svc', data_svc)
        links = loop.run_until_complete(internal_rest_svc.get_potential_links('123', '123'))
        assert 1 == len(links['links'])

    def test_apply_potential_link(self, loop, rest_svc, planning_svc, data_svc, app_svc):
        internal_rest_svc = rest_svc(loop)
        internal_rest_svc.add_service('planning_svc', planning_svc)
        internal_rest_svc.add_service('data_svc', data_svc)
        internal_rest_svc.add_service('app_svc', app_svc(loop))
        loop.run_until_complete(internal_rest_svc.get_potential_links('123', '123'))
        operation = loop.run_until_complete(data_svc.locate('operations', match=dict(id='123'))).pop()
        link = operation.potential_links[0]
        loop.run_until_complete(internal_rest_svc.apply_potential_link(link))
        assert 1 == len(operation.chain)
