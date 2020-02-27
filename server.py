import argparse
import asyncio
import logging
import pathlib
import sys

import yaml
from aiohttp import web

from app.api.rest_api import RestApi
from app.objects.c_plugin import Plugin
from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.contact_svc import ContactService
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService
from app.utility.base_world import BaseWorld


def setup_logger():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    for logger_name in logging.root.manager.loggerDict.keys():
        if logger_name in ('aiohttp.server', 'asyncio'):
            continue
        else:
            logging.getLogger(logger_name).setLevel(100)


async def build_docs():
    process = await asyncio.create_subprocess_exec('sphinx-build', 'docs/', 'docs/_build/html',
                                                   '-b', 'html', '-c', 'docs/',
                                                   stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()


async def start_server():
    await auth_svc.apply(app_svc.application, BaseWorld.get_config('users'))
    app_svc.application.router.add_static('/docs/', 'docs/_build/html', append_version=True)
    runner = web.AppRunner(app_svc.application)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', BaseWorld.get_config('port')).start()


def run_tasks(services):
    loop = asyncio.get_event_loop()
    loop.create_task(build_docs())
    loop.run_until_complete(data_svc.restore_state())
    loop.run_until_complete(RestApi(services).enable())
    loop.run_until_complete(app_svc.register_contacts())
    loop.run_until_complete(app_svc.load_plugins())
    loop.run_until_complete(data_svc.load_data([Plugin(data_dir='data')]))
    loop.run_until_complete(data_svc.load_data())
    loop.create_task(app_svc.start_sniffer_untrusted_agents())
    loop.create_task(app_svc.resume_operations())
    loop.create_task(app_svc.run_scheduler())
    loop.create_task(learning_svc.build_model())
    loop.run_until_complete(start_server())
    try:
        logging.info('All systems ready.')
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(services.get('app_svc').teardown())


if __name__ == '__main__':
    sys.path.append('')
    setup_logger()
    parser = argparse.ArgumentParser('Welcome to the system')
    parser.add_argument('-E', '--environment', required=False, default='local', help='Select an env. file to use')
    parser.add_argument('--fresh', action='store_true', required=False, default=False,
                        help='remove object_store on start')
    args = parser.parse_args()
    config = args.environment if pathlib.Path('conf/%s.yml' % args.environment).exists() else 'default'
    with open('conf/%s.yml' % config) as c:
        BaseWorld.apply_config(yaml.load(c, Loader=yaml.FullLoader))
        data_svc = DataService()
        contact_svc = ContactService(BaseWorld.strip_yml('conf/agents.yml')[0]['agent_config'])
        planning_svc = PlanningService()
        rest_svc = RestService()
        auth_svc = AuthService()
        file_svc = FileSvc(BaseWorld.strip_yml('conf/payloads.yml')[0]['payload_config'])
        learning_svc = LearningService()
        app_svc = AppService(application=web.Application())

        if args.fresh:
            asyncio.get_event_loop().run_until_complete(data_svc.destroy())
        run_tasks(services=app_svc.get_services())
