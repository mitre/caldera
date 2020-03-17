from http import HTTPStatus

from aiohttp.test_utils import unittest_run_loop

from tests.base.test_base import TestBase


class TestCoreEndponts(TestBase):

    _cookies = ''

    async def authorized_request(self, *args, **kwargs):
        if not self._cookies:
            resp = await self.client.request('POST', '/enter', allow_redirects=False,
                                             data=dict(username='admin', password='admin'))
            self._cookies = resp.cookies
        return await self.client.request(*args, cookies=self._cookies, **kwargs)

    async def get(self):
        return self.client.session()

    @unittest_run_loop
    async def test_home(self):
        resp = await self.client.request('GET', '/')
        assert resp.status == HTTPStatus.OK
        assert resp.content_type == 'text/html'

    @unittest_run_loop
    async def test_access_denied(self):
        resp = await self.client.request('GET', '/enter')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    @unittest_run_loop
    async def test_login(self):
        resp = await self.client.request('POST', '/enter', allow_redirects=False,
                                         data=dict(username='admin', password='admin'))
        assert resp.status == HTTPStatus.FOUND
        assert resp.headers.get('Location') == '/'
        assert 'API_SESSION' in resp.cookies

    @unittest_run_loop
    async def test_core(self):
        resp = await self.authorized_request('POST', '/api/rest', json=dict(index='agents'))
        assert resp.status == HTTPStatus.OK

