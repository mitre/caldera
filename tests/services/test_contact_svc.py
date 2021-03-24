import base64
import os
import pytest

from app.service.rest_svc import RestService
from app.objects.secondclass.c_result import Result


class TestProcessor:

    async def preprocess(self, blob):
        return base64.b64encode(blob)

    async def postprocess(self, blob):
        return str(base64.b64decode(blob), 'utf-8')


@pytest.fixture
def setup_contact_service(loop, data_svc, agent, ability, operation, link, adversary):
    tability = ability(tactic='discovery', technique_id='T1033', technique='Find', name='test',
                       test='d2hvYW1pCg==', description='find active user', cleanup='', executor='special_executor',
                       platform='darwin', payloads=['wifi.sh'], parsers=[], requirements=[], privilege=None,
                       variations=[])
    tability.HOOKS['special_executor'] = TestProcessor()
    loop.run_until_complete(data_svc.store(tability))
    tagent = agent(sleep_min=10, sleep_max=60, watchdog=0, executors=['special_executor'])
    loop.run_until_complete(data_svc.store(tagent))
    toperation = operation(name='sample', agents=[tagent], adversary=adversary())
    tlink = link(command='', paw=tagent.paw, ability=tability, id='5212fca4-6544-49ce-a78d-a95d30e95705')
    loop.run_until_complete(toperation.apply(tlink))
    loop.run_until_complete(data_svc.store(toperation))
    yield tlink


@pytest.mark.usefixtures(
    'app_svc',
    'data_svc',
    'file_svc',
    'learning_svc',
    'obfuscator'
)
class TestContactSvc:
    async def test_save_ability_hooks(self, setup_contact_service, contact_svc):
        test_string = b'test_string'
        link = setup_contact_service
        rest_svc = RestService()
        result = dict(
            id=link.id,
            output=str(base64.b64encode(base64.b64encode(test_string)), 'utf-8'),
            pid=0,
            status=0
        )
        await contact_svc._save(Result(**result))
        result = await rest_svc.display_result(dict(link_id=link.id))
        assert base64.b64decode(result['output']) == test_string

        # cleanup test
        try:
            os.remove(os.path.join('data', 'results', link.id))
        except FileNotFoundError:
            print('Unable to cleanup test_save_ability_hooks result file')
