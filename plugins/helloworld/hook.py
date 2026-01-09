from app.utility.base_world import BaseWorld
import logging
from aiohttp import web
from pathlib import Path
from app.service.auth_svc import AuthService

name = 'helloworld'
description = 'RBAC example plugin!'
address = 'plugin/helloworld'

async def enable(services):
    app = services.get('app_svc').application
    logger = logging.getLogger(__name__)
    plugin_dir = Path(__file__).parent  
    auth_svc = services.get('auth_svc')
    data_svc = services.get('data_svc')

    await auth_svc.create_user('dummy', 'dummy', 'red')
    print('✅ Dummy user created')

    async def landing(request):
        return web.FileResponse(plugin_dir / 'static' / 'index.html')
    
    abilities = await data_svc.locate('abilities')
    auth = await auth_svc.create_user('student', 'student', 'red')
    auth = await auth_svc.create_user('student1', 'student1', 'red')

    app.router.add_route('GET', '/plugin/helloworld/gui', landing)
    logger.warning('Hello world is now enabled')

async def disable():
    logger = logging.getLogger(__name__)
    logger.warning('Hello world is disabled')
