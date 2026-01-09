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
        router.add_get('/contacts', self.get_available_contact_reports)
        router.add_get('/contactlist', self.get_contact_list)

    @aiohttp_apispec.docs(tags=['contacts'],
                          summary='Retrieve a List of Beacons made by Agents to the specified Contact',
                          description='Returns a list of beacons made by agents to the specified contact. The response'
                                      ' is formatted as a list of dictionaries. The dictionaries have the keys `paw`,'
                                      ' `instructions`, and `date`. `paw` being the paw of the agent that made the'
                                      ' beacon. `instructions` being a list of strings (commands) executed by the'
                                      ' agent since its last beacon. `date` being a UTC date/time string.',
                          parameters=[{
                              'in': 'path',
                              'name': 'name',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'Name of the contact to get beacons for, e.g. HTTP, TCP, et cetera.'
                          }])
    async def get_contact_report(self, request: web.Request):
        contact_name = request.match_info['name']
        report = self._api_manager.get_contact_report(contact_name)
        return web.json_response(report)

    @aiohttp_apispec.docs(tags=['contacts'],
                          summary='Retrieve a List of all available Contact reports',
                          description='Returns a list of contacts that at least one agent has beaconed to.'
                                      ' As soon as any agent beacons over a given contact, the contact'
                                      ' will be returned here.')
    async def get_available_contact_reports(self, request: web.Request):
        contacts = self._api_manager.get_available_contact_reports()
        return web.json_response(contacts)

    async def get_contact_list(self, request: web.Request):
        contacts = [dict(name=c.name, description=c.description) for c in self._api_manager.contact_svc.contacts]
        return web.json_response(contacts)
