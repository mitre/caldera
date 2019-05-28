import argparse
import asyncio
import logging
import os
import ssl
import sys
from importlib import import_module

import aiohttp_jinja2
import jinja2
import yaml
from aiohttp import web
from aiohttp.web_middlewares import normalize_path_middleware
from aiohttp_session import SimpleCookieStorage, session_middleware

from app.database.core_dao import CoreDao
from app.service.auth_svc import AuthService
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.service.operation_svc import OperationService
from app.service.utility_svc import UtilityService
from app.utility.logger import Logger

SSL_CERT_FILE = 'conf/cert.pem'
SSL_KEY_FILE = 'conf/key.pem'
with open(SSL_CERT_FILE) as cert_file:
    SSL_CERT = cert_file.read()


async def background_tasks(app):
    app.loop.create_task(operation_svc.resume())


async def attach_plugins(app, services):
    services['auth_svc'].set_app(app)
    for pm in services.get('plugins'):
        plugin = getattr(pm, 'initialize')
        await plugin(app, services)
        logging.debug('Attached plugin: %s' % pm.name)
    templates = ['plugins/%s/templates' % p.name.lower() for p in services['plugins']]
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(templates))


@asyncio.coroutine
async def init(address, port, services, users):
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(SSL_CERT_FILE, SSL_KEY_FILE)
    mw = [session_middleware(SimpleCookieStorage()), normalize_path_middleware()]
    app = web.Application(middlewares=mw)
    app.on_startup.append(background_tasks)

    app.router.add_route('POST', '/file/render', services.get('file_svc').render)
    app.router.add_route('POST', '/file/download', services.get('file_svc').download)

    await services.get('data_svc').reload_database()
    for user, pwd in users.items():
        await services.get('auth_svc').register(username=user, password=pwd)
    await attach_plugins(app, services)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, address, port, ssl_context=context).start()


def main(services, host, port, users):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(host, port, services, users))
    try:
        logging.debug('Starting system at %s:%s' % (host, port))
        loop.run_forever()
    except KeyboardInterrupt:
        pass


def build_plugins(plugs):
    modules = []
    for plug in plugs if plugs else []:
        if not os.path.isdir('plugins/%s' % plug) or not os.path.isfile('plugins/%s/hook.py' % plug):
            logging.error('Problem validating the "%s" plugin. Ensure CALDERA was cloned recursively.' % plug)
            exit(0)
        modules.append(import_module('plugins.%s.hook' % plug))
    return modules


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Welcome to the system')
    parser.add_argument('-E', '--environment', required=False, default='local', help='Select an env. file to use')
    args = parser.parse_args()
    with open('conf/%s.yml' % args.environment) as c:
        config = yaml.load(c)
        logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.FATAL)
        logging.getLogger().setLevel(config['debug_level'])
        sys.path.append('')

        plugin_modules = build_plugins(config['plugins'])
        utility_svc = UtilityService()
        data_svc = DataService(CoreDao('core.db'), config['debug_level'])
        operation_svc = OperationService(data_svc=data_svc, utility_svc=utility_svc, planner=config['planner'])
        auth_svc = AuthService(data_svc=data_svc, ssl_cert=SSL_CERT)
        file_svc = FileSvc(config['stores'])
        services = dict(
            data_svc=data_svc, auth_svc=auth_svc, utility_svc=utility_svc, operation_svc=operation_svc,
            file_svc=file_svc, logger=Logger('plugin'), plugins=plugin_modules
        )
        main(services=services, host=config['host'], port=config['port'], users=config['users'])
