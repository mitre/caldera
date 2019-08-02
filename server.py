import argparse
import asyncio
import logging
import os
import sys
from importlib import import_module

import aiohttp_jinja2
import jinja2
import yaml
from aiohttp import web

from app.database.core_dao import CoreDao
from app.service.auth_svc import AuthService
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.service.operation_svc import OperationService
from app.service.parsing_svc import ParsingService
from app.service.planning_svc import PlanningService
from app.service.utility_svc import UtilityService


async def background_tasks(app):
    app.loop.create_task(operation_svc.resume())
    app.loop.create_task(data_svc.load_data(directory='data'))


def build_plugins(plugs):
    modules = []
    for plug in plugs if plugs else []:
        if not os.path.isdir('plugins/%s' % plug) or not os.path.isfile('plugins/%s/hook.py' % plug):
            print('Problem validating the "%s" plugin. Ensure CALDERA was cloned recursively.' % plug)
            exit(0)
        logging.debug('Loading plugin: %s' % plug)
        modules.append(import_module('plugins.%s.hook' % plug))
    return modules


async def attach_plugins(app, services):
    for pm in services.get('plugins'):
        plugin = getattr(pm, 'initialize')
        await plugin(app, services)
    templates = ['plugins/%s/templates' % p.name.lower() for p in services['plugins']]
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(templates))


@asyncio.coroutine
async def init(address, port, services, users):
    app = web.Application()
    await auth_svc.apply(app, users)
    app.on_startup.append(background_tasks)

    app.router.add_route('*', '/file/download', services.get('file_svc').download)
    app.router.add_route('POST', '/file/upload', services.get('file_svc').upload)

    await services.get('data_svc').load_data()
    await attach_plugins(app, services)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, address, port).start()


def main(services, host, port, users):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(host, port, services, users))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Welcome to the system')
    parser.add_argument('-E', '--environment', required=False, default='local', help='Select an env. file to use')
    args = parser.parse_args()
    with open('conf/%s.yml' % args.environment) as c:
        cfg = yaml.load(c)
        logging.getLogger('aiohttp.access').setLevel(logging.FATAL)
        logging.getLogger('aiohttp_session').setLevel(logging.FATAL)
        logging.getLogger('aiohttp.server').setLevel(logging.FATAL)
        logging.getLogger('asyncio').setLevel(logging.FATAL)
        logging.getLogger().setLevel(logging.DEBUG)
        sys.path.append('')

        plugin_modules = build_plugins(cfg['plugins'])
        utility_svc = UtilityService()
        data_svc = DataService(CoreDao('core.db', memory=cfg['memory']), utility_svc)
        logging.debug('Using an in-memory database: %s' % cfg['memory'])
        planning_svc = PlanningService(data_svc, utility_svc)
        parsing_svc = ParsingService(data_svc)
        operation_svc = OperationService(data_svc=data_svc, utility_svc=utility_svc, planning_svc=planning_svc, parsing_svc=parsing_svc)
        auth_svc = AuthService(utility_svc=utility_svc)
        logging.debug('Uploaded files will be put in %s' % cfg['exfil_dir'])
        file_svc = FileSvc(['plugins/%s/payloads' % p.name.lower() for p in plugin_modules], cfg['exfil_dir'])
        services = dict(
            data_svc=data_svc, auth_svc=auth_svc, utility_svc=utility_svc, operation_svc=operation_svc,
            file_svc=file_svc, planning_svc=planning_svc, plugins=plugin_modules
        )
        logging.debug('Serving at http://%s:%s' % (cfg['host'], cfg['port']))
        main(services=services, host=cfg['host'], port=cfg['port'], users=cfg['users'])
