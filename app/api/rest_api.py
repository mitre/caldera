import asyncio
import logging
import uuid

from aiohttp import web
from aiohttp_jinja2 import template, render_template

from app.api.packs.advanced import AdvancedPack
from app.api.packs.campaign import CampaignPack
from app.objects.secondclass.c_link import Link
from app.service.auth_svc import check_authorization
from app.utility.base_world import BaseWorld


class RestApi(BaseWorld):

    def __init__(self, services):
        self.log = logging.getLogger('rest_api')
        self.data_svc = services.get('data_svc')
        self.app_svc = services.get('app_svc')
        self.auth_svc = services.get('auth_svc')
        self.file_svc = services.get('file_svc')
        self.rest_svc = services.get('rest_svc')
        asyncio.get_event_loop().create_task(CampaignPack(services).enable())
        asyncio.get_event_loop().create_task(AdvancedPack(services).enable())

    async def enable(self):
        self.app_svc.application.router.add_static('/gui', 'static/', append_version=True)
        # unauthorized GUI endpoints
        self.app_svc.application.router.add_route('*', '/', self.landing)
        self.app_svc.application.router.add_route('*', '/enter', self.validate_login)
        self.app_svc.application.router.add_route('*', '/logout', self.logout)
        self.app_svc.application.router.add_route('GET', '/login', self.login)
        # unauthorized API endpoints
        self.app_svc.application.router.add_route('*', '/file/download', self.download)
        self.app_svc.application.router.add_route('POST', '/file/upload', self.upload_exfil_http)
        # authorized API endpoints
        self.app_svc.application.router.add_route('*', '/api/rest', self.rest_core)
        self.app_svc.application.router.add_route('POST', '/api/payload', self.upload_payload)
        self.app_svc.application.router.add_route('*', '/api/potential-links', self.handle_potential_links)
        self.app_svc.application.router.add_route('PUT', '/api/operation/state', self.rest_state_control)
        self.app_svc.application.router.add_route('PUT', '/api/operation/{operation_id}', self.rest_update_operation)

    """ BOILERPLATE """

    @template('login.html', status=401)
    async def login(self, request):
        return dict()

    async def validate_login(self, request):
        return await self.auth_svc.login_user(request)

    @template('login.html')
    async def logout(self, request):
        await self.auth_svc.logout_user(request)

    async def landing(self, request):
        access = await self.auth_svc.get_permissions(request)
        if not access:
            return render_template('login.html', request, {})
        plugins = await self.data_svc.locate('plugins', {'access': tuple(access), **dict(enabled=True)})
        data = dict(plugins=[p.display for p in plugins])
        return render_template('%s.html' % access[0].name, request, data)

    """ API ENDPOINTS """

    @check_authorization
    async def rest_core(self, request):
        try:
            access = dict(access=(await self.auth_svc.get_permissions(request)))
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
                    operation_report=lambda d: self.rest_svc.display_operation_report(d),
                    result=lambda d: self.rest_svc.display_result(d),
                    contact=lambda d: self.rest_svc.download_contact_report(d),
                    configuration=lambda d: self.rest_svc.update_config(d)
                )
            )
            if index not in options[request.method]:
                search = {**data, **access}
                return web.json_response(await self.rest_svc.display_objects(index, search))
            return web.json_response(await options[request.method][index](data))
        except Exception as e:
            self.log.error(repr(e), exc_info=True)

    async def rest_update_operation(self, request):
        i = request.match_info['operation_id']
        data = await request.json()
        operation = await self.data_svc.locate('operations', match=dict(id=int(i)))
        operation[0].autonomous = data.get('autonomous')
        return web.Response()

    @check_authorization
    async def handle_potential_links(self, request):
        data = dict(await request.json())
        options = dict(
            PUT=dict(
                func=lambda d: self.rest_svc.apply_potential_link(Link.from_json(d))
            ),
            POST=dict(
                func=lambda d: self.rest_svc.get_potential_links(**d)
            )
        )
        resp = await options[request.method]['func'](data)
        return web.json_response(resp)

    async def upload_payload(self, request):
        return await self.file_svc.save_multipart_file_upload(request, 'data/payloads/')

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
                self.log.error(repr(e))

        await _validate_request()
        await self.rest_svc.change_operation_state(body['name'], body['state'])
        return web.Response()

    async def upload_exfil_http(self, request):
        dir_name = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        exfil_dir = await self.file_svc.create_exfil_sub_directory(dir_name=dir_name)
        return await self.file_svc.save_multipart_file_upload(request, exfil_dir)

    async def download(self, request):
        try:
            payload, content, display_name = await self.file_svc.get_file(request.headers)
            headers = dict([('CONTENT-DISPOSITION', 'attachment; filename="%s"' % display_name)])
            return web.Response(body=content, headers=headers)
        except FileNotFoundError:
            return web.HTTPNotFound(body='File not found')
        except Exception as e:
            return web.HTTPNotFound(body=str(e))
