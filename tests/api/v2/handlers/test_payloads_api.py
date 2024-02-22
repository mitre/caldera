from http import HTTPStatus


class TestPayloadsApi:

    async def test_get_payloads(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/payloads', cookies=api_cookies)
        payloads_list = await resp.json()
        assert len(payloads_list) > 0
        payload = payloads_list[0]
        assert type(payload) is str

    async def test_unauthorized_get_payloads(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/payloads')
        assert resp.status == HTTPStatus.UNAUTHORIZED
