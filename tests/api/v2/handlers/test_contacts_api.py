import pytest

from http import HTTPStatus


@pytest.fixture
def contact_report_data(contact_svc):
    contact_svc.report = {
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
    return contact_svc.report


class TestContactsApi:
    async def test_get_http_contact_report(self, api_v2_client, api_cookies, contact_report_data):
        resp = await api_v2_client.get('/api/v2/contacts/http', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert output == contact_report_data['HTTP']

    async def test_get_other_contact_report(self, api_v2_client, api_cookies, contact_report_data):
        resp = await api_v2_client.get('/api/v2/contacts/html', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert output == contact_report_data['html']

    async def test_unauthorized_get_contact_report(self, api_v2_client, contact_report_data):
        resp = await api_v2_client.get('/api/v2/contacts/html')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_get_contact_report(self, api_v2_client, api_cookies, contact_report_data):
        resp = await api_v2_client.get('/api/v2/contacts/invalid_contact', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND
