import pytest

from http import HTTPStatus
from app.api.v2.managers.contact_api_manager import ContactApiManager


@pytest.fixture
def setup_report_data():
    return {
        'HTTP': [
            {
                "paw": "test_1",
                "instructions": [],
                "date": "2021-08-29 15:00:00"
            }
        ],
        'html': [
            {
                "paw": "test_2",
                "instructions": [],
                "date": "2021-08-31 15:00:00"
            }
        ]
    }


class TestContactsApi:
    async def test_get_contact_report(self, api_v2_client, api_cookies, mocker, setup_report_data, contact_svc):
        # with mocker.patch(ContactService, 'report', setup_report_data):
        #    contact_svc.report = setup_report_data
        # with mocker.patch.object(, 'get') as mock_get:
        #    mock_get.return_value = setup_report_data
        with mocker.patch.dict(ContactApiManager().contact_svc.report, setup_report_data):
            resp = await api_v2_client.get('/api/v2/contacts/http', cookies=api_cookies)
            assert resp.status == HTTPStatus.OK
            output = await resp.json()
            assert output == setup_report_data['HTTP']

    async def test_unauthorized_get_contact_report(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/contacts/html')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_get_contact_report(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/contacts/invalid_contact', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND
