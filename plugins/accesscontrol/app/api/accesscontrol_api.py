from aiohttp import web

async def add_routes(app, services):
    svc = services['accesscontrol_svc']

    app.router.add_post('/plugin/accesscontrol/user', create_user(svc))
    app.router.add_post('/plugin/accesscontrol/user/ability', assign_ability_to_user(svc))
    app.router.add_get('/plugin/accesscontrol/user/abilities', get_user_abilities(svc))

def create_user(svc):
    async def handler(request):
        data = await request.json()
        user = svc.create_user(data.get('username'))
        return web.json_response(user)
    return handler

def assign_ability_to_user(svc):
    async def handler(request):
        data = await request.json()
        user = svc.assign_ability_to_user(data.get('username'), data.get('ability'))
        return web.json_response(user)
    return handler

def get_user_abilities(svc):
    async def handler(request):
        username = request.query.get('username')
        try:
            abilities = svc.get_user_abilities(username)
            return web.json_response({'allowed_abilities': abilities})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=404)
    return handler