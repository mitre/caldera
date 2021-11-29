from aiohttp_jinja2 import template

from app.service.auth_svc import check_authorization
from app.utility.base_world import BaseWorld


class AdvancedPack(BaseWorld):

    def __init__(self, services):
        self.app_svc = services.get('app_svc')
        self.auth_svc = services.get('auth_svc')
        self.contact_svc = services.get('contact_svc')
        self.data_svc = services.get('data_svc')
        self.rest_svc = services.get('rest_svc')

    async def enable(self):
        self.app_svc.application.router.add_route('GET', '/advanced/sources', self._section_sources)
        self.app_svc.application.router.add_route('GET', '/advanced/objectives', self._section_objectives)
        self.app_svc.application.router.add_route('GET', '/advanced/planners', self._section_planners)
        self.app_svc.application.router.add_route('GET', '/advanced/contacts', self._section_contacts)
        self.app_svc.application.router.add_route('GET', '/advanced/obfuscators', self._section_obfuscators)
        self.app_svc.application.router.add_route('GET', '/advanced/configurations', self._section_configurations)
        self.app_svc.application.router.add_route('GET', '/advanced/exfills', self._section_exfil_files)

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
        return dict(config=self.get_config(), plugins=[p for p in await self.data_svc.locate('plugins')])

    @check_authorization
    @template('sources.html')
    async def _section_sources(self, request):
        access = await self.auth_svc.get_permissions(request)
        return dict(sources=[s.display for s in await self.data_svc.locate('sources', match=dict(access=tuple(access)))])

    @check_authorization
    @template('objectives.html')
    async def _section_objectives(self, request):
        access = await self.auth_svc.get_permissions(request)
        return dict(objectives=[o.display for o in await self.data_svc.locate('objectives', match=dict(access=tuple(access)))])

    @check_authorization
    @template('exfilled_files.html')
    async def _section_exfil_files(self, request):
        access = await self.auth_svc.get_permissions(request)
        return dict(exfil_dir=self.get_config('exfil_dir'), operations=[o.display for o in await self.data_svc.locate('operations', match=dict(access=tuple(access)))])
