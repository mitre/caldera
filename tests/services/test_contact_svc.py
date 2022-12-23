import base64
import json
import os
import pytest

from app.service.rest_svc import RestService
from app.objects.secondclass.c_executor import Executor
from app.objects.secondclass.c_result import Result


class TestProcessor:

    async def preprocess(self, blob):
        return base64.b64encode(blob)

    async def postprocess(self, blob):
        return str(base64.b64decode(blob), 'utf-8')


@pytest.fixture
def setup_contact_service(event_loop, data_svc, agent, ability, operation, link, adversary):
    texecutor = Executor(name='special_executor', platform='darwin', command='whoami', payloads=['wifi.sh'])
    tability = ability(tactic='discovery', technique_id='T1033', technique_name='Find', name='test',
                       description='find active user', privilege=None, executors=[texecutor])
    tability.HOOKS['special_executor'] = TestProcessor()
    event_loop.run_until_complete(data_svc.store(tability))
    tagent = agent(sleep_min=10, sleep_max=60, watchdog=0, executors=['special_executor'])
    event_loop.run_until_complete(data_svc.store(tagent))
    toperation = operation(name='sample', agents=[tagent], adversary=adversary())
    tlink = link(command='', paw=tagent.paw, ability=tability, id='5212fca4-6544-49ce-a78d-a95d30e95705',
                 executor=texecutor)
    event_loop.run_until_complete(toperation.apply(tlink))
    event_loop.run_until_complete(data_svc.store(toperation))
    yield tlink


@pytest.mark.usefixtures(
    'app_svc',
    'data_svc',
    'file_svc',
    'learning_svc',
    'obfuscator'
)
class TestContactSvc:
    async def test_save_ability_hooks(self, setup_contact_service, contact_svc, event_svc):
        test_string = b'test_string'
        err_string = b'err_string'
        test_exit_code = "-1"
        link = setup_contact_service
        rest_svc = RestService()
        result = dict(
            id=link.id,
            output=str(base64.b64encode(base64.b64encode(test_string)), 'utf-8'),
            stderr=str(base64.b64encode(err_string), 'utf-8'),
            exit_code=test_exit_code,
            pid=0,
            status=0
        )
        await contact_svc._save(Result(**result))
        result = await rest_svc.display_result(dict(link_id=link.id))
        result_dict = json.loads(base64.b64decode(result['output']))

        assert result_dict['stdout'] == test_string.decode()
        assert result_dict['stderr'] == err_string.decode()
        assert result_dict['exit_code'] == test_exit_code

        # cleanup test
        try:
            os.remove(os.path.join('data', 'results', link.id))
        except FileNotFoundError:
            print('Unable to cleanup test_save_ability_hooks result file')

    async def test_save_ability_hooks_with_no_link(self, setup_contact_service, contact_svc, event_svc, file_svc):
        test_string = b'test_string'
        err_string = b'err_string'
        test_exit_code = "0"
        # Send version with link for comparison
        result = dict(
            id="12345",
            output=str(base64.b64encode(test_string), 'utf-8'),
            stderr=str(base64.b64encode(err_string), 'utf-8'),
            exit_code=test_exit_code,
            pid=0,
            status=0
        )

        await contact_svc._save(Result(**result))

        result = file_svc.read_result_file("12345")
        result_dict = json.loads(base64.b64decode(result))
        assert result_dict['stdout'] == test_string.decode()
        assert result_dict['stderr'] == err_string.decode()
        assert result_dict['exit_code'] == test_exit_code

        # cleanup test
        try:
            os.remove(os.path.join('data', 'results', '12345'))
        except FileNotFoundError:
            print('Unable to cleanup test_save_ability_hooks_with_no_link result files')
