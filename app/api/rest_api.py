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
        self.app_svc.application.router.add_route('GET', '/upgrade', self.upgrade)


        # unauthorized API endpoints
        self.app_svc.application.router.add_route('*', '/file/download', self.download_file)
        self.app_svc.application.router.add_route('POST', '/file/upload', self.upload_file)
        # authorized API endpoints
        self.app_svc.application.router.add_route('*', '/api/rest', self.rest_core)

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

    """ UPGRADE VERSION """

    async def run(self, cmd):
        upgrade_result = {}
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
    
        stdout, stderr = await proc.communicate()
        self.log.debug(f'Command: {cmd!r} exited with {proc.returncode}')

        if cmd == 'git pull':
            command = 'upgrade_code'
        if cmd == 'git status':
            command = 'status_code'
        
        if stdout:
            # print(f'[stdout]\n{stdout.decode()}')
            output = stdout.decode().strip() ## removes 'b (byte) and \n (newline)
            if output == 'Already up to date.':
                upgrade_result[command] = output
            else:
                upgrade_result[command] = 'Caldera has been updated, please restart server.py'

        if stderr:
            self.log.debug(f'[stderr]\n{stderr.decode()}')
            # stderr = stdout.decode().strip()
            upgrade_result[command] = stderr

        return upgrade_result

    @check_authorization
    @template('upgrade.html', status=200)
    async def upgrade(self, request):       
        self.log.debug("[!] Checking if new version of Caldera is available")      
        return await self.run('git pull')

    # @check_authorization
    # @template('upgrade.html', status=200)
    # async def status(self, request):       
    #     self.log.debug("Checking status of git repo")      
    #     return await self.run('git status')

    """ API ENDPOINTS """

    @check_authorization
    async def rest_core(self, request):
        try:
            access = dict(access=tuple(await self.auth_svc.get_permissions(request)))
            data = dict(await request.json())
            index = data.pop('index')
            options = dict(
                DELETE=dict(
                    agents=lambda d: self.rest_svc.delete_agent(d),
                    operations=lambda d: self.rest_svc.delete_operation(d)
                ),
                PUT=dict(
                    adversaries=lambda d: self.rest_svc.persist_adversary(d),
                    abilities=lambda d: self.rest_svc.persist_ability(d),
                    sources=lambda d: self.rest_svc.persist_source(d),
                    planners=lambda d: self.rest_svc.update_planner(d),
                    agents=lambda d: self.rest_svc.update_agent_data(d),
                    chain=lambda d: self.rest_svc.update_chain_data(d),
                    operations=lambda d: self.rest_svc.create_operation(access, d),
                    schedule=lambda d: self.rest_svc.create_schedule(access, d),
                    link=lambda d: self.rest_svc.apply_potential_link(Link.from_json(d))
                ),
                POST=dict(
                    operation_report=lambda d: self.rest_svc.display_operation_report(d),
                    result=lambda d: self.rest_svc.display_result(d),
                    contact=lambda d: self.rest_svc.download_contact_report(d),
                    configuration=lambda d: self.rest_svc.update_config(d),
                    link=lambda d: self.rest_svc.get_potential_links(**d),
                    operation=lambda d: self.rest_svc.update_operation(**d)
                )
            )
            if index not in options[request.method]:
                search = {**data, **access}
                return web.json_response(await self.rest_svc.display_objects(index, search))
            return web.json_response(await options[request.method][index](data))
        except Exception as e:
            self.log.error(repr(e), exc_info=True)

    async def upload_file(self, request):
        dir_name = request.headers.get('Directory', None)
        if dir_name:
            return await self.file_svc.save_multipart_file_upload(request, 'data/payloads/')
        created_dir = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        saveto_dir = await self.file_svc.create_exfil_sub_directory(dir_name=created_dir)
        return await self.file_svc.save_multipart_file_upload(request, saveto_dir)

    async def download_file(self, request):
        try:
            payload, content, display_name = await self.file_svc.get_file(request.headers)
            headers = dict([('CONTENT-DISPOSITION', 'attachment; filename="%s"' % display_name)])
            return web.Response(body=content, headers=headers)
        except FileNotFoundError:
            return web.HTTPNotFound(body='File not found')
        except Exception as e:
            return web.HTTPNotFound(body=str(e))
