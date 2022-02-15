import pytest

from http import HTTPStatus
from base64 import b64encode

from app.objects.c_source import SourceSchema
from app.objects.secondclass.c_link import Link
from app.utility.base_service import BaseService


@pytest.mark.usefixtures(
    "setup_operations_api_test"
)
class TestOperationsApi:
    async def test_get_operations(self, api_v2_client, api_cookies, test_operation):
        resp = await api_v2_client.get('/api/v2/operations', cookies=api_cookies)
        operations_list = await resp.json()
        assert len(operations_list) == 1
        operation_dict = operations_list[0]
        assert operation_dict['name'] == test_operation['name']
        assert operation_dict['id'] == test_operation['id']
        assert operation_dict['group'] == test_operation['group']
        assert operation_dict['state'] == test_operation['state']

    async def test_unauthorized_get_operations(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/operations')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_operation_by_id(self, api_v2_client, api_cookies, test_operation):
        resp = await api_v2_client.get('/api/v2/operations/123', cookies=api_cookies)
        operation_dict = await resp.json()
        assert operation_dict['name'] == test_operation['name']
        assert operation_dict['id'] == test_operation['id']

    async def test_unauthorized_get_operation_by_id(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/operations/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_operation_by_id(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/operations/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_get_operation_report_no_payload(self, api_v2_client, api_cookies, mocker, async_return,
                                                   test_operation):
        with mocker.patch('app.objects.c_operation.Operation.all_facts') as mock_all_facts:
            mock_all_facts.return_value = async_return([])
            resp = await api_v2_client.post('/api/v2/operations/123/report', cookies=api_cookies)
            report = await resp.json()
            assert report['name'] == test_operation['name']
            assert report['jitter'] == test_operation['jitter']
            assert report['planner'] == test_operation['planner']['name']
            assert report['adversary']['name'] == test_operation['adversary']['name']
            assert report['start']

    async def test_get_operation_report_agent_output_disabled(self, api_v2_client, api_cookies, mocker, async_return,
                                                              test_operation):
        with mocker.patch('app.objects.c_operation.Operation.all_facts') as mock_all_facts:
            mock_all_facts.return_value = async_return([])
            payload = {'enable_agent_output': False}
            resp = await api_v2_client.post('/api/v2/operations/123/report', cookies=api_cookies, json=payload)
            report = await resp.json()
            assert report['name'] == test_operation['name']
            assert report['jitter'] == test_operation['jitter']
            assert report['planner'] == test_operation['planner']['name']
            assert report['adversary']['name'] == test_operation['adversary']['name']
            assert report['start']

    async def test_get_operation_report_agent_output_enabled(self, api_v2_client, api_cookies, mocker, async_return,
                                                             test_operation, expected_link_output):
        with mocker.patch('app.objects.c_operation.Operation.all_facts') as mock_all_facts:
            mock_all_facts.return_value = async_return([])
            with mocker.patch('app.objects.c_operation.Operation.decode_bytes') as mock_decode:
                mock_decode.return_value = expected_link_output
                with mocker.patch('app.service.file_svc.FileSvc.read_result_file') as mock_readfile:
                    mock_readfile.return_value = ''
                    payload = {'enable_agent_output': True}
                    resp = await api_v2_client.post('/api/v2/operations/123/report', cookies=api_cookies, json=payload)
                    report = await resp.json()
                    assert report['name'] == test_operation['name']
                    assert report['jitter'] == test_operation['jitter']
                    assert report['planner'] == test_operation['planner']['name']
                    assert report['adversary']['name'] == test_operation['adversary']['name']
                    assert report['start']

    async def test_unauthorized_get_operation_report(self, api_v2_client):
        resp = await api_v2_client.post('/api/v2/operations/123/report')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_operation_report(self, api_v2_client, api_cookies):
        resp = await api_v2_client.post('/api/v2/operations/999/report', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_get_operation_event_logs_no_payload(self, api_v2_client, api_cookies, mocker, async_return,
                                                       test_operation, finished_link, test_agent):
        resp = await api_v2_client.post('/api/v2/operations/123/event-logs', cookies=api_cookies)
        event_logs = await resp.json()
        assert event_logs[1]['command'] == finished_link['command']
        assert event_logs[1]['agent_metadata']['paw'] == test_agent.schema.dump(test_agent)['paw']
        assert event_logs[1]['operation_metadata']['operation_name'] == test_operation['name']
        assert not event_logs[1].get('output')

    async def test_get_operation_event_logs_agent_output_disabled(self, api_v2_client, api_cookies, mocker,
                                                                  async_return, test_operation, finished_link,
                                                                  test_agent):
        payload = {'enable_agent_output': False}
        resp = await api_v2_client.post('/api/v2/operations/123/event-logs', cookies=api_cookies, json=payload)
        event_logs = await resp.json()
        assert event_logs[1]['command'] == finished_link['command']
        assert event_logs[1]['agent_metadata']['paw'] == test_agent.schema.dump(test_agent)['paw']
        assert event_logs[1]['operation_metadata']['operation_name'] == test_operation['name']
        assert not event_logs[1].get('output')

    async def test_get_operation_event_logs_agent_output_enabled(self, api_v2_client, api_cookies, mocker, async_return,
                                                                 test_operation, finished_link, test_agent,
                                                                 expected_link_output):
        with mocker.patch('app.objects.c_operation.Operation.decode_bytes') as mock_decode:
            mock_decode.return_value = expected_link_output
            with mocker.patch('app.service.file_svc.FileSvc.read_result_file') as mock_readfile:
                mock_readfile.return_value = ''
                payload = {'enable_agent_output': True}
                resp = await api_v2_client.post('/api/v2/operations/123/event-logs', cookies=api_cookies, json=payload)
                event_logs = await resp.json()
                assert event_logs[1]['command'] == finished_link['command']
                assert event_logs[1]['agent_metadata']['paw'] == test_agent.schema.dump(test_agent)['paw']
                assert event_logs[1]['operation_metadata']['operation_name'] == test_operation['name']
                assert event_logs[1]['output'] == expected_link_output
                assert not event_logs[0].get('output')

    async def test_unauthorized_get_operation_event_logs(self, api_v2_client):
        resp = await api_v2_client.post('/api/v2/operations/123/event-logs')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_operation_event_logs(self, api_v2_client, api_cookies):
        resp = await api_v2_client.post('/api/v2/operations/999/event-logs', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_operation(self, api_v2_client, api_cookies):
        payload = dict(name='post_test', planner={'id': '123'},
                       adversary={'adversary_id': '123', 'name': 'ad-hoc'}, source={'id': '123'})
        resp = await api_v2_client.post('/api/v2/operations', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        op_exists = await BaseService.get_service('data_svc').locate('operations', {'name': 'post_test'})
        assert op_exists
        op_data = await resp.json()
        assert op_data['name'] == payload['name']
        assert op_data['start']
        assert op_data['planner']['id'] == payload['planner']['id']
        assert op_data['adversary']['name'] == payload['adversary']['name']
        assert op_data['source']['id'] == payload['source']['id']

    async def test_duplicate_create_operation(self, api_v2_client, api_cookies, test_operation):
        payload = dict(name='post_test', id=test_operation['id'], planner={'id': '123'},
                       adversary={'adversary_id': '123'}, source={'id': '123'})
        resp = await api_v2_client.post('/api/v2/operations', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_create_operation_existing_relationships(self, api_v2_client, api_cookies,
                                                           test_source_existing_relationships):
        payload = dict(name='op_existing_relationships', id='456', planner={'id': '123'},
                       adversary={'adversary_id': '123'},
                       source=SourceSchema().dump(test_source_existing_relationships))
        resp = await api_v2_client.post('/api/v2/operations', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        op_data = await resp.json()
        assert op_data['name'] == payload['name']
        assert op_data['start']
        assert op_data['planner']['id'] == payload['planner']['id']
        assert op_data['source']['id'] == payload['source']['id']
        assert len(op_data['source']['relationships']) == len(payload['source']['relationships'])

    async def test_create_finished_operation(self, api_v2_client, api_cookies, test_operation):
        payload = dict(name='post_test', id='111', planner={'id': '123'},
                       adversary={'adversary_id': '123'}, source={'id': '123'}, state='finished')
        resp = await api_v2_client.post('/api/v2/operations', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_unauthorized_create_operation(self, api_v2_client):
        payload = dict(name='post_test', planner={'id': '123'},
                       adversary={'adversary_id': '123'}, source={'id': '123'})
        resp = await api_v2_client.post('/api/v2/operations', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_operation(self, api_v2_client, api_cookies, mocker, async_return, test_operation):
        op_manager_path = 'app.api.v2.managers.operation_api_manager.OperationApiManager.validate_operation_state'
        with mocker.patch(op_manager_path) as mock_validate:
            mock_validate.return_value = async_return(True)
            payload = dict(state='running', obfuscator='base64')
            resp = await api_v2_client.patch('/api/v2/operations/123', cookies=api_cookies, json=payload)
            assert resp.status == HTTPStatus.OK
            op = (await BaseService.get_service('data_svc').locate('operations', {'id': '123'}))[0]
            assert op.state == payload['state']
            assert op.obfuscator == payload['obfuscator']
            assert op.id == test_operation['id']
            assert op.name == test_operation['name']
            assert op.planner.planner_id == test_operation['planner']['id']

    async def test_unauthorized_update_operation(self, api_v2_client):
        payload = dict(state='running', obfuscator='base64')
        resp = await api_v2_client.patch('/api/v2/operations/123', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_update(self, api_v2_client, api_cookies):
        payload = dict(state='running', obfuscator='base64')
        resp = await api_v2_client.patch('/api/v2/operations/999', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_disallowed_fields_update_operation(self, api_v2_client, api_cookies, mocker, async_return, test_operation):
        op_manager_path = 'app.api.v2.managers.operation_api_manager.OperationApiManager.validate_operation_state'
        with mocker.patch(op_manager_path) as mock_validate:
            mock_validate.return_value = async_return(True)
            payload = dict(name='new operation', id='500')
            resp = await api_v2_client.patch('/api/v2/operations/123', cookies=api_cookies, json=payload)
            assert resp.status == HTTPStatus.OK
            op = (await BaseService.get_service('data_svc').locate('operations', {'id': '123'}))[0]
            assert op.id == test_operation['id']
            assert op.name == test_operation['name']
            assert op.planner.name == test_operation['planner']['name']

    async def test_update_finished_operation(self, api_v2_client, api_cookies, setup_finished_operation,
                                             finished_operation_payload):
        payload = dict(state='running', obfuscator='base64')
        op_id = finished_operation_payload['id']
        resp = await api_v2_client.patch(f'/api/v2/operations/{op_id}', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_get_links(self, api_v2_client, api_cookies, active_link):
        resp = await api_v2_client.get('/api/v2/operations/123/links', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        links = await resp.json()
        assert len(links) == 2
        assert links[0]['id'] == active_link['id']
        assert links[0]['paw'] == active_link['paw']
        assert links[0]['command'] == active_link['command']

    async def test_unauthorized_get_links(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/operations/123/links')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_operation_link(self, api_v2_client, api_cookies, active_link):
        resp = await api_v2_client.get('/api/v2/operations/123/links/456', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        link = await resp.json()
        assert link['id'] == active_link['id']
        assert link['paw'] == active_link['paw']
        assert link['command'] == active_link['command']

    async def test_unauthorized_get_operation_link(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/operations/123/links/456')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_operation_link(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/operations/999/links/123', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_nonexistent_link_get_operation_link(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/operations/123/links/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_update_operation_link(self, api_v2_client, api_cookies, active_link):
        original_command = active_link['command']
        payload = dict(command='whoami')
        resp = await api_v2_client.patch('/api/v2/operations/123/links/456', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        op = (await BaseService.get_service('data_svc').locate('operations', {'id': '123'}))[0]
        assert op.chain[0].command != original_command
        assert op.chain[0].command == str(b64encode(payload['command'].encode()), 'utf-8')
        assert op.chain[0].id == active_link['id']
        assert op.chain[0].paw == active_link['paw']

    async def test_unauthorized_update_operation_link(self, api_v2_client):
        payload = dict(command='bHM=')
        resp = await api_v2_client.patch('/api/v2/operations/123/links/456', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_update_operation_link(self, api_v2_client, api_cookies):
        payload = dict(command='bHM=')
        resp = await api_v2_client.patch('/api/v2/operations/999/links/123', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_nonexistent_link_update_operation_link(self, api_v2_client, api_cookies):
        payload = dict(command='bHM=')
        resp = await api_v2_client.patch('/api/v2/operations/123/links/999', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_update_finished_operation_link(self, api_v2_client, api_cookies):
        payload = dict(command='bHM=', status=-1)
        resp = await api_v2_client.patch('/api/v2/operations/123/links/789', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.FORBIDDEN

    async def test_get_potential_links(self, api_v2_client, api_cookies, mocker, async_return):
        BaseService.get_service('rest_svc').build_potential_abilities = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_abilities.return_value = async_return([])
        expected_link = Link(command='whoami', paw='123456', id='789')
        BaseService.get_service('rest_svc').build_potential_links = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_links.return_value = async_return([expected_link])
        resp = await api_v2_client.get('/api/v2/operations/123/potential-links', cookies=api_cookies)
        result = await resp.json()
        assert len(result) == 1
        assert result[0]['id'] == expected_link.id
        assert result[0]['paw'] == expected_link.paw
        assert result[0]['command'] == expected_link.command

    async def test_unauthorized_get_potential_links(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/operations/123/potential-links')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_potential_links(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/operations/999/potential-links', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_get_potential_links_by_paw(self, api_v2_client, api_cookies, mocker, async_return, ability, executor):
        BaseService.get_service('rest_svc').build_potential_abilities = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_abilities.return_value = async_return([])
        expected_link = Link(command='whoami', paw='123', id='789')
        BaseService.get_service('rest_svc').build_potential_links = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_links.return_value = async_return([expected_link])
        resp = await api_v2_client.get('/api/v2/operations/123/potential-links/123', cookies=api_cookies)
        result = await resp.json()
        assert len(result) == 1
        assert result[0]['id'] == expected_link.id
        assert result[0]['paw'] == expected_link.paw
        assert result[0]['command'] == expected_link.command

    async def test_unauthorized_get_potential_links_by_paw(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/operations/123/potential-links/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_potential_links_by_paw(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/operations/999/potential-links/123', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_nonexistent_agent_get_potential_links_by_paw(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/operations/123/potential-links/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_potential_link(self, api_v2_client, api_cookies, mocker, async_return):
        with mocker.patch('app.objects.c_operation.Operation.apply') as mock_apply:
            mock_apply.return_value = async_return(None)
            payload = {
                "paw": "123",
                "executor": {
                    "platform": "linux",
                    "name": "sh",
                    "command": "ls -a"
                },
                "status": -1
            }
            resp = await api_v2_client.post('/api/v2/operations/123/potential-links', cookies=api_cookies, json=payload)
            result = await resp.json()
            assert result['paw'] == payload['paw']
            assert result['id']
            assert result['ability']['name'] == 'Manual Command'
            assert result['executor']['platform'] == payload['executor']['platform']

    async def test_unauthorized_create_potential_links(self, api_v2_client):
        payload = {
            "paw": "123",
            "executor": {
                "platform": "linux",
                "name": "sh",
                "command": "ls -a"
            },
            "status": -1
        }
        resp = await api_v2_client.post('/api/v2/operations/123/potential-links', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_create_potential_links(self, api_v2_client, api_cookies):
        payload = {
            "paw": "123",
            "executor": {
                "platform": "linux",
                "name": "sh",
                "command": "ls -a"
            },
            "status": -1
        }
        resp = await api_v2_client.post('/api/v2/operations/999/potential-links', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_get_operation_link_result(self, api_v2_client, api_cookies, finished_link, mocker):
        with mocker.patch('app.service.file_svc.FileSvc.read_result_file') as mock_read_result:
            encoded_result = str(b64encode('user'.encode()), 'utf-8')
            mock_read_result.return_value = encoded_result
            resp = await api_v2_client.get('/api/v2/operations/123/links/789/result', cookies=api_cookies)
            assert resp.status == HTTPStatus.OK
            output = await resp.json()
            assert output['link']['id'] == finished_link['id']
            assert output['link']['paw'] == finished_link['paw']
            assert output['link']['command'] == finished_link['command']
            assert output['result'] == encoded_result

    async def test_unauthorized_get_operation_link_result(self, api_v2_client, finished_link):
        resp = await api_v2_client.get('/api/v2/operations/123/links/789/result')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_operation_link_no_result(self, api_v2_client, api_cookies, active_link):
        resp = await api_v2_client.get('/api/v2/operations/123/links/456/result', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert output['result'] == ''
        assert output['link']['paw'] == active_link['paw']
        assert output['link']['id'] == active_link['id']
        assert output['link']['command'] == active_link['command']

    async def test_nonexistent_get_operation_link_result(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/operations/123/links/999/result', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND
