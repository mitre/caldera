import base64
import json
import os
import asyncio
import uuid
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
async def setup_contact_service(data_svc, agent, ability, operation, link, adversary):
    texecutor = Executor(name='special_executor', platform='darwin', command='whoami', payloads=['wifi.sh'])
    tability = ability(tactic='discovery', technique_id='T1033', technique_name='Find', name='test',
                       description='find active user', privilege=None, executors=[texecutor])
    tability.HOOKS['special_executor'] = TestProcessor()
    await data_svc.store(tability)
    tagent = agent(sleep_min=10, sleep_max=60, watchdog=0, executors=['special_executor'])
    await data_svc.store(tagent)
    toperation = operation(name='sample', agents=[tagent], adversary=adversary())
    tlink = link(command='', paw=tagent.paw, ability=tability, id='5212fca4-6544-49ce-a78d-a95d30e95705',
                 executor=texecutor)
    await toperation.apply(tlink)
    await data_svc.store(toperation)
    yield tlink


@pytest.fixture
async def setup_learning_contact_service(data_svc, agent, ability, operation, link, adversary):
    texecutor = Executor(name='psh', platform='windows', command='whoami')
    tability = ability(tactic='discovery', technique_id='T1033', technique_name='Find', name='learn-test',
                       description='learn active host data', privilege=None, executors=[texecutor])
    await data_svc.store(tability)
    tagent = agent(sleep_min=10, sleep_max=60, watchdog=0, platform='windows', executors=['psh'])
    await data_svc.store(tagent)
    toperation = operation(name='sample-learning', agents=[tagent], adversary=adversary(), use_learning_parsers=True)
    tlink = link(command='', paw=tagent.paw, ability=tability, id=str(uuid.uuid4()),
                 executor=texecutor)
    await toperation.apply(tlink)
    await data_svc.store(toperation)
    yield toperation, tlink


@pytest.mark.usefixtures(
    'app_svc',
    'data_svc',
    'file_svc',
    'knowledge_svc',
    'learning_svc',
    'fire_event_mock'
)
class TestContactSvc:
    async def test_save_ability_hooks(self, setup_contact_service, contact_svc):
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

    async def test_save_ability_hooks_with_no_link(self, setup_contact_service, contact_svc, file_svc):
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

    async def test_save_result_with_unique_id_updates_operation_facts(self, setup_learning_contact_service,
                                                                      contact_svc):
        operation, link = setup_learning_contact_service
        result = Result(
            id=link.unique,
            output=str(base64.b64encode('10.10.10.10'.encode('utf-8')), 'utf-8'),
            pid=0,
            status=0
        )

        await contact_svc._save(result)

        learned_facts = await operation.all_facts()
        assert len(learned_facts) == 1
        assert learned_facts[0].trait == 'host.ip.address'
        assert learned_facts[0].value == '10.10.10.10'

        try:
            os.remove(os.path.join('data', 'results', link.unique))
        except FileNotFoundError:
            print('Unable to cleanup test_save_result_with_unique_id_updates_operation_facts result file')

    async def test_save_waits_for_learning_before_marking_link_finished(self, setup_learning_contact_service,
                                                                        contact_svc, mocker):
        operation, link = setup_learning_contact_service
        learning_started = asyncio.Event()
        allow_learning_to_finish = asyncio.Event()
        learning_svc = contact_svc.get_service('learning_svc')
        app_svc = contact_svc.get_service('app_svc')

        async def slow_learn(*args, **kwargs):
            learning_started.set()
            await allow_learning_to_finish.wait()

        patched_learn = mocker.AsyncMock(side_effect=slow_learn)
        with mocker.patch.object(learning_svc, 'learn', new=patched_learn):
            save_task = asyncio.create_task(contact_svc._save(Result(
                id=link.unique,
                output=str(base64.b64encode('10.10.10.10'.encode('utf-8')), 'utf-8'),
                pid=0,
                status=0
            )))

            await asyncio.wait_for(learning_started.wait(), timeout=2)
            saved_link = await app_svc.find_link(link.unique)
            assert not save_task.done()
            assert saved_link.finish is None

            allow_learning_to_finish.set()
            await asyncio.wait_for(save_task, timeout=2)

        assert patched_learn.await_count == 1
        saved_link = await app_svc.find_link(link.unique)
        assert saved_link.finish is not None

        try:
            os.remove(os.path.join('data', 'results', link.unique))
        except FileNotFoundError:
            print('Unable to cleanup test_save_waits_for_learning_before_marking_link_finished result file')
