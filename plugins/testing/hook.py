from aiohttp import web
from aiohttp_jinja2 import template
from app.service.auth_svc import check_authorization
from pathlib import Path
from plugins.testing.app.rbac_store import RbacStore
from plugins.testing.app.rbac_mw import RbacMiddleware
from aiohttp_jinja2 import template
from app.service.auth_svc import check_authorization

name = 'testing'
description = 'RBAC demo plugin'
address = '/plugin/testing/gui'
global _store
_store = RbacStore()

async def enable(services):
    app = services.get('app_svc').application

    # init our JSON store
    await _store.load()

    # --- mount static at a sub-path to avoid collisions with /plugin/testing/gui
    static_dir = Path(__file__).parent / 'static'
    static_dir.mkdir(exist_ok=True)
    app.router.add_static('/plugin/testing/static', path=str(static_dir), append_version=True)

    api = RbacApi(services)

    # GUI + RBAC API routes
    app.router.add_route('GET', address, api.splash)
    app.router.add_route('GET',  '/plugin/testing/rbac/roles',   api.roles_list)
    app.router.add_route('POST', '/plugin/testing/rbac/roles',   api.roles_upsert)
    app.router.add_route('GET',  '/plugin/testing/rbac/users',   api.users_list)
    app.router.add_route('POST', '/plugin/testing/rbac/users',   api.users_upsert)
    app.router.add_route('GET',  '/plugin/testing/rbac/groups',  api.groups_list)
    app.router.add_route('POST', '/plugin/testing/rbac/groups',  api.groups_upsert)
    app.router.add_route('GET',  '/plugin/testing/rbac/allowed', api.allowed_for_user)
    app.router.add_route('GET', '/plugin/testing/abilities', api.abilities_list)
    app.router.add_route('GET', '/plugin/testing/rbac/gui', api.rbac_gui)

    static_dir = Path(__file__).parent / 'static'
    app.router.add_static('/plugin/testing/static', path=str(static_dir), append_version=True)

    rbac_mw = RbacMiddleware(services, _store)
    app.middlewares.append(rbac_mw.handle)

class RbacApi:
    def __init__(self, services):
        self.services = services
        self.auth_svc = services.get('auth_svc')
        self.data_svc = services.get('data_svc')

    @check_authorization
    @template('rbac_view.html')
    async def rbac_gui(self, request):
        return {}  # template-only; Vue will fetch data

    # --- GUI page ---
    @check_authorization
    @template('splash.html')
    async def splash(self, request):
        return dict(message='RBAC plugin is live. API under /plugin/testing/rbac/*')

    # --- RBAC endpoints (same as before) ---
    @check_authorization
    async def roles_list(self, request):
        return web.json_response(await _store.list_roles())

    @check_authorization
    async def roles_upsert(self, request):
        body = await request.json()
        await _store.upsert_role(body['name'], body.get('allowed_abilities', []))
        return web.json_response({'ok': True})

    @check_authorization
    async def users_list(self, request):
        return web.json_response(await _store.list_users())

    @check_authorization
    async def users_upsert(self, request):
        body = await request.json()
        await _store.upsert_user(
            body['username'], body.get('group', 'red'),
            body.get('roles', []), body.get('allowed_abilities', [])
        )
        return web.json_response({'ok': True})

    @check_authorization
    async def groups_list(self, request):
        return web.json_response(await _store.list_groups())

    @check_authorization
    async def groups_upsert(self, request):
        body = await request.json()
        await _store.upsert_group(body['name'], body.get('members', []), body.get('roles', []))
        return web.json_response({'ok': True})

    @check_authorization
    async def allowed_for_user(self, request):
        username = request.rel_url.query.get('username')
        if not username:
            raise web.HTTPBadRequest(text='username is required')
        allowed = await _store.resolve_allowed_abilities_for_user(username)
        return web.json_response({'username': username, 'allowed_abilities': allowed})
    # NEW: list abilities for the dropdowns
    @check_authorization
    async def abilities_list(self, request):
        abilities = await self.data_svc.locate('abilities')
        # return the safe “display” view so the UI can use ability_id + name
        return web.json_response({
            "abilities": [a.display for a in abilities]
        })