import pytest

from http import HTTPStatus


CONTACTS_REPORT = {
    'HTTP': [
        {
            "paw": "test_1",
            "instructions": [],
            "date": "2021-08-29 15:00:00"
        }
    ],
    'HTML': [
        {
            "paw": "test_2",
            "instructions": [],
            "date": "2021-08-31 15:00:00"
        }
    ]
}


@pytest.fixture
def contact_report_data(contact_svc):
    contact_svc.report = CONTACTS_REPORT
    return contact_svc.report


class TestContactsApi:
    async def test_get_uppercase_contact_report(self, api_v2_client, api_cookies, contact_report_data):
        resp = await api_v2_client.get('/api/v2/contacts/HTTP', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert output == CONTACTS_REPORT['HTTP']

    async def test_get_lowercase_contact_report(self, api_v2_client, api_cookies, contact_report_data):
        resp = await api_v2_client.get('/api/v2/contacts/html', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert output == contact_report_data['HTML']

    async def test_unauthorized_get_contact_report(self, api_v2_client, contact_report_data):
        resp = await api_v2_client.get('/api/v2/contacts/HTML')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_get_contact_report(self, api_v2_client, api_cookies, contact_report_data):
        resp = await api_v2_client.get('/api/v2/contacts/invalid_contact', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_get_available_contact_report(self, api_v2_client, api_cookies, contact_report_data):
        resp = await api_v2_client.get('/api/v2/contacts', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert output == ['HTTP', 'HTML']
