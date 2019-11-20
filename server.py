import argparse
import asyncio
import logging
import os
import pathlib
import sys
from importlib import import_module
from subprocess import Popen, DEVNULL

import aiohttp_jinja2
import jinja2
import yaml
from aiohttp import web

from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.service.planning_svc import PlanningService


async def background_tasks(app):
    loop = asyncio.get_event_loop()
    loop.create_task(application.start_sniffer_untrusted_agents())
    loop.create_task(application.resume_operations())
    loop.create_task(data_svc.load_data(directory='data'))
    loop.create_task(data_svc.restore_state())
    loop.create_task(application.run_scheduler())


def build_plugins(plugs):
    modules = []
    for plug in plugs if plugs else []:
        if not os.path.isdir('plugins/%s' % plug) or not os.path.isfile('plugins/%s/hook.py' % plug):
            print('Problem validating the "%s" plugin. Ensure CALDERA was cloned recursively.' % plug)
            exit(0)
        logging.debug('Loading plugin: %s' % plug)
        try:
            if os.path.isfile('plugins/%s/requirements.txt' % plug):
                Popen(['pip', 'install', '-r', 'plugins/%s/requirements.txt' % plug], stdout=DEVNULL)
        except Exception:
            print('Problem installing PIP requirements automatically. Try doing this manually.')
        modules.append(import_module('plugins.%s.hook' % plug))
    return modules


async def attach_plugins(app, services):
    for pm in services.get('app_svc').get_plugins():
        plugin = getattr(pm, 'initialize')
        await plugin(app, services)
    templates = ['plugins/%s/templates' % p.name.lower() for p in services.get('app_svc').get_plugins()]
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(templates))


async def init(address, port, services, users):
    app = web.Application()
    await auth_svc.apply(app, users)
    app.on_startup.append(background_tasks)

    app.router.add_route('*', '/file/download', services.get('file_svc').download)
    app.router.add_route('POST', '/file/upload', services.get('file_svc').upload_exfil)

    await attach_plugins(app, services)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, address, port).start()


def set_logging_state():
    state = logging.FATAL
    if cfg['debug']:
        state = logging.ERROR
    logging.getLogger('aiohttp.access').setLevel(state)
    logging.getLogger('aiohttp_session').setLevel(state)
    logging.getLogger('aiohttp.server').setLevel(state)
    logging.getLogger('asyncio').setLevel(state)
    logging.getLogger().setLevel(logging.DEBUG)


def main(services, host, port, users):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(host, port, services, users))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(data_svc.save_state())
        logging.debug('[!] shutting down server...good-bye')


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Welcome to the system')
    parser.add_argument('-E', '--environment', required=False, default='local', help='Select an env. file to use')
    parser.add_argument('--fresh', action='store_true', required=False, default=False,
                        help='remove object_store on start')
    args = parser.parse_args()

    config = args.environment if pathlib.Path('conf/%s.yml' % args.environment).exists() else 'default'
    with open('conf/%s.yml' % config) as c:
        cfg = yaml.load(c, Loader=yaml.FullLoader)
        set_logging_state()
        sys.path.append('')

        plugin_modules = build_plugins(cfg['plugins'])
        data_svc = DataService()
        planning_svc = PlanningService()
        auth_svc = AuthService(cfg['api_key'])
        file_svc = FileSvc([p.name.lower() for p in plugin_modules], cfg['exfil_dir'])
        application = AppService(config=cfg, plugins=plugin_modules)

        if args.fresh:
            asyncio.get_event_loop().run_until_complete(data_svc.clear())

        logging.debug('Agents will be considered untrusted after %s seconds of silence' % cfg['untrusted_timer'])
        logging.debug('Uploaded files will be put in %s' % cfg['exfil_dir'])
        logging.debug('Serving at http://%s:%s' % (cfg['host'], cfg['port']))
        main(services=data_svc.get_services(), host=cfg['host'], port=cfg['port'], users=cfg['users'])
