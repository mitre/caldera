from http import HTTPStatus


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

    async def test_unauthorized_get_contact_report(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/contacts/html')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_get_contact_report(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/contacts/invalid_contact', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND
