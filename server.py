import argparse
import asyncio
import logging
import os
import random
import ssl
import sys
from importlib import import_module

import aiohttp_jinja2
import jinja2
import yaml
from aiohttp import web
from aiohttp.web_middlewares import normalize_path_middleware
from aiohttp_session import SimpleCookieStorage, session_middleware
from pyfiglet import Figlet

from app.database.core_dao import CoreDao
from app.service.auth_svc import AuthService
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.service.operation_svc import OperationService
from app.service.utility_svc import UtilityService
from app.terminal.custom_shell import CustomShell
from app.utility.logger import Logger

SSL_CERT_FILE = 'conf/cert.pem'
SSL_KEY_FILE = 'conf/key.pem'
with open(SSL_CERT_FILE) as cert_file:
    SSL_CERT = cert_file.read()


async def background_tasks(app):
    app.loop.create_task(operation_svc.resume())
    app.loop.create_task(terminal.start_shell())


async def attach_plugins(app, services):
    services['auth_svc'].set_app(app)
    for pm in services.get('plugins'):
        plugin = getattr(pm, 'initialize')
        await plugin(app, services)
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
        print('...Created user: %s:%s' % (user, pwd))
    await attach_plugins(app, services)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, address, port, ssl_context=context).start()


def welcome_msg(host, port):
    custom_fig = Figlet(font='contrast')
    new_font = random.choice(custom_fig.getFonts())
    custom_fig.setFont(font=new_font)
    print(custom_fig.renderText('caldera'))
    print('Enter help or go to https://%s:%s in a browser' % (host, port))


def main(services, host, port, sockets, users):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(host, port, services, users))
    try:
        loop = asyncio.get_event_loop()
        for sock in sockets:
            print('...Socket opened on port %s' % sock)
            handler = asyncio.start_server(terminal.accept_sessions, host, sock, loop=loop)
            loop.run_until_complete(handler)
        loop.run_forever()
    except KeyboardInterrupt:
        pass


def build_plugins(plugs):
    modules = []
    for plug in plugs if plugs else []:
        if not os.path.isdir('plugins/%s' % plug) or not os.path.isfile('plugins/%s/hook.py' % plug):
            print('Problem validating the "%s" plugin. Ensure CALDERA was cloned recursively.' % plug)
            exit(0)
        modules.append(import_module('plugins.%s.hook' % plug))
    return modules


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Welcome to the system')
    parser.add_argument('-E', '--environment', required=False, default='local', help='Select an env. file to use')
    args = parser.parse_args()
    with open('conf/%s.yml' % args.environment) as c:
        cfg = yaml.load(c)
        logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.FATAL)
        logging.getLogger().setLevel('CRITICAL')
        sys.path.append('')

        plugin_modules = build_plugins(cfg['plugins'])
        utility_svc = UtilityService()
        data_svc = DataService(CoreDao('core.db'))
        operation_svc = OperationService(data_svc=data_svc, utility_svc=utility_svc, planner=cfg['planner'])
        auth_svc = AuthService(data_svc=data_svc, ssl_cert=SSL_CERT)
        file_svc = FileSvc(cfg['stores'])
        services = dict(
            data_svc=data_svc, auth_svc=auth_svc, utility_svc=utility_svc, operation_svc=operation_svc,
            file_svc=file_svc, plugins=plugin_modules
        )
        terminal = CustomShell(services)
        welcome_msg(cfg['host'], cfg['port'])
        main(services=services, host=cfg['host'], port=cfg['port'], sockets=cfg['sockets'], users=cfg['users'])
