import aiohttp_apispec
from aiohttp import web
import asyncio, os, sys

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_plugin import Plugin, PluginSchema
from app.utility.base_world import BaseWorld


class PluginApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='plugins', obj_class=Plugin, schema=PluginSchema, ram_key='plugins',
                         id_property='name', auth_svc=services['auth_svc'])
        self.services = services 
        self._api_manager = BaseApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/plugins', self.get_plugins)
        router.add_get('/plugins/{name}', self.get_plugin_by_name)
        router.add_post('/plugins/{name}/enable', self.enable_plugin)
        router.add_post('/plugins/disable', self.disable_plugins)
        router.add_get('/plugins/build-status', self.build_status)

    @aiohttp_apispec.docs(tags=['plugins'],
                          summary='Retrieve all plugins',
                          description='Returns a list of all available plugins in the system, including directory, description,'
                          'and active status. Supply fields from the `PluginSchema` to the include and exclude fields of the '
                          '`BaseGetAllQuerySchema` in the request body to filter retrieved plugins.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(PluginSchema(many=True, partial=True),
                                     description='Returns a list in `PluginSchema` format of all available plugins in the system.')
    async def get_plugins(self, request: web.Request):
        plugins = await self.get_all_objects(request)
        return web.json_response(plugins)

    @aiohttp_apispec.docs(tags=['plugins'],
                          summary='Retrieve plugin by name',
                          description='If plugin was found with a matching name, an object containing information about the plugin is returned.',
                          parameters=[{
                                'in': 'path',
                                'name': 'name',
                                'description': 'The name of the plugin',
                                'schema': {'type': 'string'},
                                'required': 'true'
                            }])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(PluginSchema(partial=True),
                                     description='Returns a plugin in `PluginSchema` format with the requested name, if it exists.')
    async def get_plugin_by_name(self, request: web.Request):
        plugin = await self.get_object(request)
        return web.json_response(plugin)

    @aiohttp_apispec.docs(
            tags=['plugins'],
            summary='Enable plugin',
            description='Enables a plugin, builds GUI if required, and signals restart.'
        )
    async def enable_plugin(self, request: web.Request):
        plugin_name = request.match_info["name"]

        plugin_manager = self.services.get("plugin_manager")
        app_svc = self.services.get("app_svc")

        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
        build_gui = bool(body.get("build_gui", True))

        # 1) persist enabled plugin
        enabled_plugins = BaseWorld.get_config(name="main", prop="plugins") or []

        if plugin_name not in enabled_plugins:
            enabled_plugins.append(plugin_name)

        # ✅ persist enabled plugin in runtime config
        BaseWorld.set_config(
            name="main",
            prop="plugins",
            value=enabled_plugins
        )
        if build_gui:
            # ✅ mark runtime state (NOT persisted)
            BaseWorld.set_config(
                name="main",
                prop="restarting",
                value=True
            )

        try:
            await app_svc._save_configurations()

        except Exception as e:
            print(f"Error saving configurations: {e}")

        # 2) schedule background work (DO NOT await)
        asyncio.create_task(self._enable_build_restart(plugin_manager, plugin_name, build_gui))

        # 3) return immediately
        return web.json_response({
            "enabled": True,
            "restart_required": build_gui
        })

    @aiohttp_apispec.docs(
            tags=['plugins'],
            summary='Disable plugins',
            description='Disables plugins, rebuilds UI, and restarts Caldera.'
        )
    async def disable_plugins(self, request: web.Request):
        plugin_manager = self.services.get("plugin_manager")
        app_svc = self.services.get("app_svc")

        body = await request.json()
        plugins_to_disable = body.get("plugins", []) or []

        # 1) read currently enabled
        enabled_plugins = BaseWorld.get_config(name="main", prop="plugins") or []

        # (optional safety) prevent disabling core plugins
        core = set(getattr(plugin_manager, "CORE_PLUGINS", []))
        plugins_to_disable = [p for p in plugins_to_disable if p not in core]

        # 2) compute remaining (THIS is the key constraint you described)
        remaining_plugins = [p for p in enabled_plugins if p not in plugins_to_disable]

        # 3) if nothing changed, do nothing
        if remaining_plugins == enabled_plugins:
            return web.json_response({
                "disabled": [],
                "restart_required": False
            })

        # 4) persist remaining enabled plugins
        BaseWorld.set_config(name="main", prop="plugins", value=remaining_plugins)
         
        await app_svc._save_configurations()

        # runtime-only flag (do not persist if your system saves all BaseWorld props)
        BaseWorld.set_config(name="main", prop="restarting", value=True)

        # 5) background rebuild + restart (do not await)
        asyncio.create_task(self._disable_build_restart(plugin_manager, remaining_plugins))

        return web.json_response({
            "disabled": plugins_to_disable,
            "restart_required": True
        })
    async def _enable_build_restart(self, plugin_manager, plugin_name, build_gui):
        await asyncio.sleep(0.5)

        print("[plugin_manager] starting async enable/build")

        try:
            await plugin_manager.enable_plugin(
                plugin_name,
                build_gui=build_gui,
                install_deps=True
            )
        except Exception:
            import traceback
            traceback.print_exc()
            return

        if build_gui:
            print("[plugin_manager] restarting caldera after GUI build")

            # small delay so logs flush
            await asyncio.sleep(0.5)

            os.execv(sys.executable, [sys.executable] + sys.argv)

    async def _disable_build_restart(self, plugin_manager, remaining_plugins):
        await asyncio.sleep(0.5)

        print("[plugin_manager] rebuilding GUI after plugin disable")

        try:
            # reuse existing build pipeline
            await plugin_manager._build_plugin_gui_if_needed("magma")
        except Exception:
            import traceback
            traceback.print_exc()
            return

        await asyncio.sleep(0.5)

        os.execv(sys.executable, [sys.executable] + sys.argv)

    async def build_status(self, request):
        plugin_manager = self.services.get("plugin_manager")

        return web.json_response(plugin_manager.build_state)
