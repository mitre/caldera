import logging
import traceback
import uuid

from aiohttp import web
from aiohttp_jinja2 import template

from app.service.auth_svc import check_authorization
from app.utility.base_world import BaseWorld


class RestApi(BaseWorld):

    def __init__(self, services):
        self.data_svc = services.get('data_svc')
        self.app_svc = services.get('app_svc')
        self.auth_svc = services.get('auth_svc')
        self.contact_svc = services.get('contact_svc')
        self.file_svc = services.get('file_svc')
        self.rest_svc = services.get('rest_svc')

    async def enable(self):
        self.app_svc.application.router.add_static('/gui', 'static/', append_version=True)
        # authorized sections
        self.app_svc.application.router.add_route('GET', '/section/agents', self.section_agent)
        self.app_svc.application.router.add_route('GET', '/section/adversaries', self.section_adversaries)
        self.app_svc.application.router.add_route('GET', '/section/operations', self.section_operations)
        self.app_svc.application.router.add_route('GET', '/section/sources', self.section_sources)
        self.app_svc.application.router.add_route('GET', '/section/planners', self.section_planners)
        self.app_svc.application.router.add_route('GET', '/section/contacts', self.section_contacts)
        self.app_svc.application.router.add_route('GET', '/section/obfuscators', self.section_obfuscators)
        self.app_svc.application.router.add_route('GET', '/section/configurations', self.section_configurations)
        # unauthorized GUI endpoints
        self.app_svc.application.router.add_route('*', '/enter', self.validate_login)
        self.app_svc.application.router.add_route('*', '/logout', self.logout)
        self.app_svc.application.router.add_route('GET', '/login', self.login)
        # authorized API endpoints
        self.app_svc.application.router.add_route('*', '/', self.landing)
        self.app_svc.application.router.add_route('*', '/plugin/chain/full', self.rest_full)
        self.app_svc.application.router.add_route('*', '/plugin/chain/rest', self.rest_api)
        self.app_svc.application.router.add_route('PUT', '/plugin/chain/potential-links', self.add_potential_link)
        self.app_svc.application.router.add_route('POST', '/plugin/chain/potential-links', self.find_potential_links)
        self.app_svc.application.router.add_route('POST', '/plugin/chain/payload', self.upload_payload)
        self.app_svc.application.router.add_route('PUT', '/plugin/chain/operation/state', self.rest_state_control)
        self.app_svc.application.router.add_route('PUT', '/plugin/chain/operation/{operation_id}', self.rest_update_operation)
        self.app_svc.application.router.add_route('POST', '/ability', self.ability_endpoint)
        # unauthorized agent endpoints
        self.app_svc.application.router.add_route('POST', '/internals', self.internals)
        self.app_svc.application.router.add_route('*', '/file/download', self.download)
        self.app_svc.application.router.add_route('POST', '/file/upload', self.upload_exfil_http)

    @check_authorization
    @template('agents.html')
    async def section_agent(self, request):
        agents = [h.display for h in await self.data_svc.locate('agents')]
        return dict(agents=agents)

    @check_authorization
    @template('adversaries.html')
    async def section_adversaries(self, request):
        abilities = await self.data_svc.locate('abilities')
        tactics = set([a.tactic.lower() for a in abilities])
        payloads = await self.rest_svc.list_payloads()
        adversaries = [a.display for a in await self.data_svc.locate('adversaries')]
        return dict(adversaries=adversaries, exploits=[a.display for a in abilities], payloads=payloads, tactics=tactics)

    @check_authorization
    @template('operations.html')
    async def section_operations(self, request):
        hosts = [h.display for h in await self.data_svc.locate('agents')]
        groups = list(set(([h['group'] for h in hosts])))
        adversaries = [a.display for a in await self.data_svc.locate('adversaries')]
        sources = [s.display for s in await self.data_svc.locate('sources')]
        planners = [p.display for p in await self.data_svc.locate('planners')]
        obfuscators = [o.display for o in await self.data_svc.locate('obfuscators')]
        operations = [o.display for o in await self.data_svc.locate('operations')]
        return dict(operations=operations, groups=groups, adversaries=adversaries, sources=sources, planners=planners,
                    obfuscators=obfuscators)

    @check_authorization
    @template('configurations.html')
    async def section_configurations(self, request):
        return dict(config=self.get_config())

    @check_authorization
    @template('obfuscators.html')
    async def section_obfuscators(self, request):
        obfuscators = [o.display for o in await self.data_svc.locate('obfuscators')]
        return dict(obfuscators=obfuscators)

    @check_authorization
    @template('planners.html')
    async def section_planners(self, request):
        planners = [p.display for p in await self.data_svc.locate('planners')]
        return dict(planners=planners)

    @check_authorization
    @template('contacts.html')
    async def section_contacts(self, request):
        contacts = [dict(name=c.name, description=c.description) for c in self.contact_svc.contacts]
        return dict(contacts=contacts)

    @check_authorization
    @template('sources.html')
    async def section_sources(self, request):
        sources = [s.display for s in await self.data_svc.locate('sources')]
        return dict(sources=sources)

    @template('login.html', status=401)
    async def login(self, request):
        return dict()

    @template('login.html')
    async def logout(self, request):
        await self.auth_svc.logout_user(request)

    async def validate_login(self, request):
        return await self.auth_svc.login_user(request)

    @template('home.html')
    @check_authorization
    async def landing(self, request):
        try:
            plugins = [p.display for p in await self.data_svc.locate('plugins', match=dict(enabled=True))]
            return dict(plugins=plugins)
        except web.HTTPFound as e:
            raise e
        except Exception as e:
            logging.error('[!] landing: %s' % e)

    async def upload_payload(self, request):
        return await self.file_svc.save_multipart_file_upload(request, 'data/payloads/')

    @check_authorization
    async def ability_endpoint(self, request):
        data = dict(await request.json())
        abilities = await self.rest_svc.find_abilities(**data)
        return web.json_response(dict(abilities=[a.display for a in abilities]))

    @check_authorization
    async def find_potential_links(self, request):
        data = dict(await request.json())
        links = await self.rest_svc.get_potential_links(**data)
        return web.json_response(dict(links=[l.display for l in links]))

    @check_authorization
    async def add_potential_link(self, request):
        data = dict(await request.json())
        await self.rest_svc.apply_potential_link(data)
        return web.json_response(dict())

    async def rest_full(self, request):
        try:
            base = await self.rest_core(request)
            base[0]['abilities'] = [a.display for a in await self.data_svc.locate('abilities')]
            return web.json_response(base)
        except Exception:
            pass

    async def rest_api(self, request):
        try:
            base = await self.rest_core(request)
            return web.json_response(base)
        except Exception:
            pass

    @check_authorization
    async def rest_core(self, request):
        """
        This function is under construction until all objects have been converted from SQL tables
        :param request:
        :return:
        """
        try:
            data = dict(await request.json())
            index = data.pop('index')
            options = dict(
                DELETE=dict(
                    agent=lambda d: self.rest_svc.delete_agent(d),
                    operation=lambda d: self.rest_svc.delete_operation(d)
                ),
                PUT=dict(
                    adversary=lambda d: self.rest_svc.persist_adversary(d),
                    ability=lambda d: self.rest_svc.persist_ability(d),
                    source=lambda d: self.rest_svc.persist_source(d),
                    planner=lambda d: self.rest_svc.update_planner(d),
                    agent=lambda d: self.rest_svc.update_agent_data(d),
                    chain=lambda d: self.rest_svc.update_chain_data(d),
                    operation=lambda d: self.rest_svc.create_operation(d),
                    schedule=lambda d: self.rest_svc.create_schedule(d),
                ),
                POST=dict(
                    ability=lambda d: self.rest_svc.display_objects('abilities', d),
                    adversary=lambda d: self.rest_svc.display_objects('adversaries', d),
                    planners=lambda d: self.rest_svc.display_objects('planners', d),
                    agent=lambda d: self.rest_svc.display_objects('agents', d),
                    operation=lambda d: self.rest_svc.display_objects('operations', d),
                    source=lambda d: self.rest_svc.display_objects('sources', d),
                    plugins=lambda d: self.rest_svc.display_objects('plugins', d),
                    operation_report=lambda d: self.rest_svc.display_operation_report(d),
                    result=lambda d: self.rest_svc.display_result(d),
                    contact=lambda d: self.rest_svc.download_contact_report(d),
                    configuration=lambda d: self.rest_svc.update_config(d)
                )
            )
            if index not in options[request.method]:
                return await self.rest_svc.display_objects(index, data)
            return await options[request.method][index](data)
        except Exception:
            traceback.print_exc()

    async def rest_update_operation(self, request):
        i = request.match_info['operation_id']
        data = await request.json()
        operation = await self.data_svc.locate('operations', match=dict(id=int(i)))
        operation[0].autonomous = data.get('autonomous')
        return web.Response()

    async def rest_state_control(self, request):
        body = await request.json()
        state = body.get('state')

        async def _validate_request():
            try:
                op = await self.data_svc.locate('operations', dict(id=body['name']))
                if not len(op):
                    raise web.HTTPNotFound
                elif await op[0].is_finished():
                    raise web.HTTPBadRequest(body='This operation has already finished.')
                elif state not in op[0].states.values():
                    raise web.HTTPBadRequest(body='state must be one of {}'.format(op[0].states.values()))
                elif state == op[0].states['FINISHED']:
                    await op[0].close()
            except Exception as e:
                print(e)

        await _validate_request()
        await self.rest_svc.change_operation_state(body['name'], body['state'])
        return web.Response()

    async def internals(self, request):
        options = dict(
            pin=lambda d: self.rest_svc.get_link_pin(d)
        )
        data = dict(await request.json())
        resp = await options[request.headers.get('property')](data)
        return web.json_response(resp)

    async def upload_exfil_http(self, request):
        dir_name = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        exfil_dir = await self.file_svc.create_exfil_sub_directory(dir_name=dir_name)
        return await self.file_svc.save_multipart_file_upload(request, exfil_dir)

    async def download(self, request):
        """
        Accept a request with a required header, file, and an optional header, platform, and download the file.
        :param request:
        :return: a multipart file via HTTP
        """
        try:
            payload, content, display_name = await self.file_svc.get_file(request.headers)
            headers = dict([('CONTENT-DISPOSITION', 'attachment; filename="%s"' % display_name)])
            return web.Response(body=content, headers=headers)
        except FileNotFoundError:
            return web.HTTPNotFound(body='File not found')
        except Exception as e:
            return web.HTTPNotFound(body=str(e))
