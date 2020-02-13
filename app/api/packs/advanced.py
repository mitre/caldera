import asyncio

from aiohttp_jinja2 import template

from app.service.auth_svc import check_authorization
from app.utility.base_world import BaseWorld


class AdvancedPack(BaseWorld):

    def __init__(self, services):
        self.display_name = 'advanced'
        self.access = self.Access.APP
        self.endpoints = dict(
            sources='/%s/sources' % self.display_name,
            planners='/%s/planners' % self.display_name,
            contacts='/%s/contacts' % self.display_name,
            obfuscators='/%s/obfuscators' % self.display_name,
            configurations='/%s/configurations' % self.display_name
        )
        self.app_svc = services.get('app_svc')
        self.auth_svc = services.get('auth_svc')
        self.contact_svc = services.get('contact_svc')
        self.data_svc = services.get('data_svc')
        self.rest_svc = services.get('rest_svc')
        asyncio.get_event_loop().create_task(self.enable)

    async def enable(self):
        self.app_svc.application.router.add_route('GET', self.endpoints['sources'], self._section_sources)
        self.app_svc.application.router.add_route('GET', self.endpoints['planners'], self._section_planners)
        self.app_svc.application.router.add_route('GET', self.endpoints['contacts'], self._section_contacts)
        self.app_svc.application.router.add_route('GET', self.endpoints['obfuscators'], self._section_obfuscators)
        self.app_svc.application.router.add_route('GET', self.endpoints['configurations'], self._section_configurations)

    """ PRIVATE """

    @check_authorization
    @template('planners.html')
    async def _section_planners(self, request):
        planners = [p.display for p in await self.data_svc.locate('planners')]
        return dict(planners=planners)

    @check_authorization
    @template('contacts.html')
    async def _section_contacts(self, request):
        contacts = [dict(name=c.name, description=c.description) for c in self.contact_svc.contacts]
        return dict(contacts=contacts)

    @check_authorization
    @template('obfuscators.html')
    async def _section_obfuscators(self, request):
        obfuscators = [o.display for o in await self.data_svc.locate('obfuscators')]
        return dict(obfuscators=obfuscators)

    @check_authorization
    @template('configurations.html')
    async def _section_configurations(self, request):
        return dict(config=self.get_config())

    @check_authorization
    @template('sources.html')
    async def _section_sources(self, request):
        access = [p for p in await self.auth_svc.get_permissions(request)]
        return dict(sources=[s.display for s in await self.data_svc.locate('sources', match=tuple(access))])
