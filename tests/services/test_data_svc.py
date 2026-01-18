import pytest

import asyncio
import glob
import json
import os
import shutil
import yaml

from unittest import mock
from unittest.mock import patch, call

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.c_planner import Planner
from app.objects.c_plugin import Plugin
from app.objects.secondclass.c_executor import Executor
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.utility.base_world import BaseWorld


PAYLOAD_CONFIG_YAMLS = {
    'path1': [yaml.safe_load('''
---
id: testid1
name: Plugin1 Payloads
standard_payloads:
  file.exe:
    description: file desc
    id: fileid1
  file.ps1:
    description: file desc
    id: fileid2
special_payloads:
  file.go:
    description: file desc
    id: specialid1
    service: stockpile_svc
    function: funcname
extensions:
  .donut: plugins.stockpile.app.donut.donut_handler
''')],
    'path2': [yaml.safe_load('''
---
id: testid2
name: Plugin1 Payloads 2
standard_payloads:
  file.py:
    description: file desc
    id: fileid3
  file.txt:
    description: file desc
    id: fileid4
special_payloads:
  file.cpp:
    description: file desc
    id: specialid2
    service: stockpile_svc
    function: funcname
''')],
    'path3': [yaml.safe_load('''
---
id: testid3
name: Plugin2 Payloads
special_payloads:
  special.py:
    description: file desc
    id: specialid3
    service: stockpile_svc
    function: funcname
  file.cpp:
    description: overridden desc
    id: overridden
    service: stockpile_svc
    function: overridden
extensions:
  .testext: handler
''')],
}


ABILITY_YAMLS = {
    'TESTV0ABILITYID': [yaml.safe_load('''
- id: TESTV0ABILITYID
  name: Account-type Admin Enumerator
  description: Use PowerView to query the Active Directory server to determine remote admins
  tactic: discovery
  technique:
    attack_id: T1069.002
    name: "Permission Groups Discovery: Domain Groups"
  platforms:
    windows:
      psh:
        command: |
          testcommand
        parsers:
          plugins.stockpile.app.parsers.netlocalgroup:
          - source: remote.host.fqdn
            edge: has_admin
            target: domain.user.name
        payloads:
        - powerview.ps1
  singleton: True
  requirements:
    - plugins.stockpile.app.requirements.not_exists:
      - source: remote.host.fqdn
        edge: has_admin
    - plugins.stockpile.app.requirements.basic:
      - source: backup.admin.ability
        edge: first_failed
    - plugins.stockpile.app.requirements.basic:
      - source: domain.user.name
        edge: has_password
        target: domain.user.password
    - plugins.stockpile.app.requirements.reachable:
      - source: remote.host.fqdn
        edge: isAccessibleFrom
''')]
}


def strip_payload_yaml(path):
    return PAYLOAD_CONFIG_YAMLS.get(path, [])


def strip_ability_yaml(path):
    return ABILITY_YAMLS.get(path, [])


def async_mock_return(to_return):
    mock_future = asyncio.Future()
    mock_future.set_result(to_return)
    return mock_future


@pytest.fixture
def dir_to_delete():
    to_delete = '/tmp/caldera_test_delete_dir'
    os.makedirs(to_delete)
    yield to_delete

    if os.path.exists(to_delete):
        try:
            shutil.rmtree(to_delete)
        except OSError:
            pass


class TestDataService:
    mock_payload_config = dict()

    def test_no_duplicate_adversary(self, event_loop, data_svc):
        event_loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', atomic_ordering=list())
        ))
        event_loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', atomic_ordering=list())
        ))
        adversaries = event_loop.run_until_complete(data_svc.locate('adversaries'))

        assert len(adversaries) == 1
        for x in adversaries:
            json.dumps(x.display)

    def test_no_duplicate_planner(self, event_loop, data_svc):
        event_loop.run_until_complete(data_svc.store(Planner(name='test', planner_id='some_id', module='some.path.here', params=None, description='description')))
        event_loop.run_until_complete(data_svc.store(Planner(name='test', planner_id='some_id', module='some.path.here', params=None, description='description')))
        planners = event_loop.run_until_complete(data_svc.locate('planners'))

        assert len(planners) == 1
        for x in planners:
            json.dumps(x.display)

    def test_multiple_agents(self, event_loop, data_svc):
        event_loop.run_until_complete(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        event_loop.run_until_complete(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        agents = event_loop.run_until_complete(data_svc.locate('agents'))

        assert len(agents) == 2
        for x in agents:
            json.dumps(x.display)

    def test_no_duplicate_ability(self, event_loop, data_svc):
        executor = Executor(name='special_executor', platform='darwin', command='whoami', payloads=['wifi.sh'])
        event_loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique_name='T1033', name='test',
                    description='find active user', privilege=None, executors=[executor])
        ))
        event_loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique_name='T1033', name='test',
                    description='find active user', privilege=None, executors=[executor])
        ))
        abilities = event_loop.run_until_complete(data_svc.locate('abilities'))

        assert len(abilities) == 1

    def test_operation(self, event_loop, data_svc):
        adversary = event_loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', atomic_ordering=list())
        ))
        event_loop.run_until_complete(data_svc.store(Operation(name='my first op', agents=[], adversary=adversary)))

        operations = event_loop.run_until_complete(data_svc.locate('operations'))
        assert len(operations) == 1
        for x in operations:
            json.dumps(x.display)

    def test_remove(self, event_loop, data_svc):
        a1 = event_loop.run_until_complete(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        agents = event_loop.run_until_complete(data_svc.locate('agents', match=dict(paw=a1.paw)))
        assert len(agents) == 1
        event_loop.run_until_complete(data_svc.remove('agents', match=dict(paw=a1.paw)))
        agents = event_loop.run_until_complete(data_svc.locate('agents', match=dict(paw=a1.paw)))
        assert len(agents) == 0

    def test_no_autogen_cleanup_cmds(self, event_loop, data_svc):
        cleanup_executor = Executor(name='sh', platform='linux', cleanup='rm #{payload}')
        event_loop.run_until_complete(data_svc.store(
            Ability(ability_id='4cd4eb44-29a7-4259-91ae-e457b283a880', tactic='defense-evasion', technique_id='T1070.004',
                    technique_name='Indicator Removal on Host: File Deletion', name='Delete payload',
                    description='Remove a downloaded payload file', privilege=None, executors=[cleanup_executor])
        ))
        executor = Executor(name='special_executor', platform='darwin', command='whoami', payloads=['wifi.sh'])
        event_loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique_name='T1033', name='test',
                    description='find active user', privilege=None, executors=[executor])
        ))
        event_loop.run_until_complete(data_svc._verify_abilities())
        abilities = event_loop.run_until_complete(data_svc.locate('abilities', dict(ability_id='123')))

        for ability in abilities:
            for executor in ability.executors:
                assert not executor.cleanup

    @mock.patch.object(BaseWorld, 'strip_yml', wraps=strip_payload_yaml)
    @mock.patch.object(DataService, '_apply_special_payload_hooks', return_value=async_mock_return(None))
    @mock.patch.object(DataService, '_apply_special_extension_hooks', return_value=async_mock_return(None))
    def test_load_payloads(self, mock_ext_hooks, mock_payload_hooks, mock_strip_yml, event_loop, data_svc):
        def _mock_apply_payload_config(config=None, **_):
            TestDataService.mock_payload_config = config

        test_plugin = Plugin(data_dir='test_plugin/data')
        test_plugin2 = Plugin(data_dir='test_plugin2/data')
        with patch.object(glob, 'iglob', return_value=['path1', 'path2']) as mock_iglob:
            with patch.object(BaseWorld, 'apply_config', wraps=_mock_apply_payload_config) as mock_apply_config:
                with patch.object(DataService, 'get_config', return_value=self.mock_payload_config):
                    event_loop.run_until_complete(data_svc._load_payloads(test_plugin))
        mock_iglob.assert_called_once_with('test_plugin/data/payloads/*.yml', recursive=False)
        mock_strip_yml.assert_has_calls([call('path1'), call('path2')])
        mock_payload_hooks.assert_has_calls([
            call(PAYLOAD_CONFIG_YAMLS['path1'][0]['special_payloads']),
            call(PAYLOAD_CONFIG_YAMLS['path2'][0]['special_payloads']),
        ], any_order=True)
        mock_ext_hooks.assert_has_calls([
            call(PAYLOAD_CONFIG_YAMLS['path1'][0]['extensions']),
        ], any_order=True)

        expected_config_part1 = {
            'standard_payloads': {
                'file.exe': PAYLOAD_CONFIG_YAMLS['path1'][0]['standard_payloads']['file.exe'],
                'file.ps1': PAYLOAD_CONFIG_YAMLS['path1'][0]['standard_payloads']['file.ps1'],
                'file.py': PAYLOAD_CONFIG_YAMLS['path2'][0]['standard_payloads']['file.py'],
                'file.txt': PAYLOAD_CONFIG_YAMLS['path2'][0]['standard_payloads']['file.txt'],
            },
            'special_payloads': {
                'file.go': PAYLOAD_CONFIG_YAMLS['path1'][0]['special_payloads']['file.go'],
                'file.cpp': PAYLOAD_CONFIG_YAMLS['path2'][0]['special_payloads']['file.cpp'],
            },
            'extensions': {
                '.donut': PAYLOAD_CONFIG_YAMLS['path1'][0]['extensions']['.donut'],
            }
        }
        mock_apply_config.assert_called_once_with(name='payloads', config=expected_config_part1)

        with patch.object(glob, 'iglob', return_value=['path3']) as mock_iglob2:
            with patch.object(BaseWorld, 'apply_config', wraps=_mock_apply_payload_config) as mock_apply_config2:
                with patch.object(DataService, 'get_config', return_value=self.mock_payload_config):
                    event_loop.run_until_complete(data_svc._load_payloads(test_plugin2))
        mock_iglob2.assert_called_once_with('test_plugin2/data/payloads/*.yml', recursive=False)
        mock_strip_yml.assert_called_with('path3')
        mock_payload_hooks.assert_called_with(PAYLOAD_CONFIG_YAMLS['path3'][0]['special_payloads'])
        mock_ext_hooks.assert_called_with(PAYLOAD_CONFIG_YAMLS['path3'][0]['extensions'])

        expected_config_part2 = {
            'standard_payloads': {
                'file.exe': PAYLOAD_CONFIG_YAMLS['path1'][0]['standard_payloads']['file.exe'],
                'file.ps1': PAYLOAD_CONFIG_YAMLS['path1'][0]['standard_payloads']['file.ps1'],
                'file.py': PAYLOAD_CONFIG_YAMLS['path2'][0]['standard_payloads']['file.py'],
                'file.txt': PAYLOAD_CONFIG_YAMLS['path2'][0]['standard_payloads']['file.txt'],
            },
            'special_payloads': {
                'file.go': PAYLOAD_CONFIG_YAMLS['path1'][0]['special_payloads']['file.go'],
                # test override
                'file.cpp': PAYLOAD_CONFIG_YAMLS['path3'][0]['special_payloads']['file.cpp'],
                'special.py': PAYLOAD_CONFIG_YAMLS['path3'][0]['special_payloads']['special.py'],
            },
            'extensions': {
                '.donut': PAYLOAD_CONFIG_YAMLS['path1'][0]['extensions']['.donut'],
                '.testext': PAYLOAD_CONFIG_YAMLS['path3'][0]['extensions']['.testext'],
            }
        }
        mock_apply_config2.assert_called_once_with(name='payloads', config=expected_config_part2)

    @mock.patch.object(BaseWorld, 'strip_yml', wraps=strip_ability_yaml)
    async def test_load_v0_ability_file(self, mock_strip_yml, data_svc):
        await data_svc.load_ability_file('TESTV0ABILITYID', data_svc.Access.RED)
        search_results = await data_svc.locate('abilities', match=dict(ability_id='TESTV0ABILITYID'))
        assert len(search_results) == 1
        result = search_results[0]
        assert result.name == 'Account-type Admin Enumerator'
        assert result.description == 'Use PowerView to query the Active Directory server to determine remote admins'
        assert result.tactic == 'discovery'
        assert result.technique_name == 'Permission Groups Discovery: Domain Groups'
        assert result.technique_id == 'T1069.002'
        assert result.singleton
        result_executor = result.find_executor('psh', 'windows')
        assert result_executor.command == 'testcommand'
        assert result_executor.payloads == ['powerview.ps1']
        assert len(result_executor.parsers) == 1
        result_parser = result_executor.parsers[0]
        assert result_parser.unique == 'plugins.stockpile.app.parsers.netlocalgroup'
        assert len(result_parser.parserconfigs) == 1
        result_parser_cfg = result_parser.parserconfigs[0]
        assert result_parser_cfg.source == 'remote.host.fqdn'
        assert result_parser_cfg.edge == 'has_admin'
        assert result_parser_cfg.target == 'domain.user.name'
        assert not result_parser_cfg.custom_parser_vals
        assert len(result.requirements) == 4

    def test_delete_file(self, dir_to_delete):
        to_delete = os.path.join(dir_to_delete, 'caldera_test_delete_file')
        open(to_delete, 'a').close()
        assert os.path.exists(to_delete)
        DataService._delete_file(to_delete)
        assert not os.path.exists(to_delete)
        DataService._delete_file(to_delete)  # no-op delete

        assert os.path.exists(dir_to_delete)
        DataService._delete_file(dir_to_delete)
        assert not os.path.exists(dir_to_delete)

    async def test_destroy(self, data_svc, dir_to_delete):
        def mock_glob(input):
            if 'abilities' in input:
                return ['/tmp/caldera_test_delete_dir/calderadummyfile.txt']
            else:
                return []

        with open('/tmp/caldera_test_delete_dir/calderadummyfile.txt', 'w') as input_file:
            input_file.write('test')

        with mock.patch.object(glob, 'glob', side_effect=mock_glob):
            with mock.patch.object(os.path, 'join', return_value='/tmp/caldera_test_delete_dir/test.tar.gz'):
                with mock.patch.object(os, 'mkdir', return_value=True):
                    await data_svc.destroy()
        assert not os.path.exists('/tmp/caldera_test_delete_dir/calderadummyfile.txt')
        assert os.path.exists('/tmp/caldera_test_delete_dir/test.tar.gz')

    @mock.patch.object(os.path, 'exists', return_value=True)
    async def test_save_and_restore_state(self, mock_exists, data_svc, dir_to_delete, ability):
        test_abil = ability(ability_id='testsaverestoreabil', name='testsaverestoreabil')
        await data_svc.store(test_abil)
        with mock.patch.object(os.path, 'join', return_value='/tmp/caldera_test_delete_dir/object_store'):
            with mock.patch.object(FileSvc, 'find_file_path', return_value=(None, '/tmp/caldera_test_delete_dir/object_store')):
                await data_svc.save_state()
                assert os.path.exists('/tmp/caldera_test_delete_dir/object_store')
                assert await data_svc.locate('abilities', match=dict(ability_id='testsaverestoreabil'))
                await data_svc.remove('abilities', match=dict(ability_id='testsaverestoreabil'))
                assert not await data_svc.locate('abilities', match=dict(ability_id='testsaverestoreabil'))
                await data_svc.restore_state()
                assert await data_svc.locate('abilities', match=dict(ability_id='testsaverestoreabil'))

    async def test_search_object(self, data_svc, ability):
        test_abil = ability(ability_id='tosearchfor', name='testsaverestoreabil', tags=['tag1', 'tag2'])
        await data_svc.store(test_abil)
        result = await data_svc.search('tag1', 'abilities')
        assert len(result) == 1
        assert result[0] == test_abil
        result = await data_svc.search('tag2', 'abilities')
        assert len(result) == 1
        assert result[0] == test_abil
        result = await data_svc.search('dne', 'abilities')
        assert not result
