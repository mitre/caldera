from aiohttp import web
import  aiohttp_jinja2

helloworld_routes = web.RouteTableDef()

@helloworld_routes.get('/plugin/helloworld/gui')
async def gui(request):
    services = request.app['services']
    auth_svc = services.get('auth_svc')
    user = await auth_svc.get_current_user(request)

    if 'dummy' in user.get('groups', []):
        return web.Response(text='X dummy user not allowed here')

    return aiohttp_jinja2.render_template('gui.html', request, {})