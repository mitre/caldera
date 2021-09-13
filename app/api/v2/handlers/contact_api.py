import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.managers.contact_api_manager import ContactApiManager


class ContactApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self._api_manager = ContactApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'],
                                              contact_svc=services['contact_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/contacts/{name}', self.get_contact_report)

    @aiohttp_apispec.docs(tags=['contacts'])
    async def get_contact_report(self, request: web.Request):
        contact_name = request.match_info['name'].upper()
        report = self._api_manager.get_contact_report(contact_name)
        return web.json_response(report)
