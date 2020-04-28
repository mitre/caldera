import argparse
import asyncio
import logging
import os
import pathlib
import sys

from aiohttp import web

from app.api.rest_api import RestApi
from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.contact_svc import ContactService
from app.service.data_svc import DataService
from app.service.event_svc import EventService
from app.service.file_svc import FileSvc
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService
from app.utility.base_world import BaseWorld


def setup_logger(level=logging.DEBUG):
    logging.basicConfig(level=level,
                        format='%(asctime)s - %(levelname)-5s (%(filename)s:%(lineno)s %(funcName)s) %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
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
    await web.TCPSite(runner, BaseWorld.get_config('host'), BaseWorld.get_config('port')).start()


def run_tasks(services):
    loop = asyncio.get_event_loop()
    loop.create_task(build_docs())
    loop.create_task(app_svc.validate_requirements())
    loop.run_until_complete(data_svc.restore_state())
    loop.run_until_complete(RestApi(services).enable())
    loop.run_until_complete(app_svc.register_contacts())
    loop.run_until_complete(app_svc.load_plugins(args.plugins))
    loop.run_until_complete(data_svc.load_data(loop.run_until_complete(data_svc.locate('plugins', dict(enabled=True)))))
    loop.run_until_complete(app_svc.load_plugin_expansions(loop.run_until_complete(data_svc.locate('plugins', dict(enabled=True)))))
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
    def list_str(values):
        return values.split(',')
    sys.path.append('')
    parser = argparse.ArgumentParser('Welcome to the system')
    parser.add_argument('-E', '--environment', required=False, default='local', help='Select an env. file to use')
    parser.add_argument("-l", "--log", dest="logLevel", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help="Set the logging level", default='DEBUG')
    parser.add_argument('--fresh', action='store_true', required=False, default=False,
                        help='remove object_store on start')
    parser.add_argument('-P', '--plugins', required=False, default=os.listdir('plugins'),
                        help='Start up with a single plugin', type=list_str)

    args = parser.parse_args()
    setup_logger(getattr(logging, args.logLevel))
    config = args.environment if pathlib.Path('conf/%s.yml' % args.environment).exists() else 'default'
    BaseWorld.apply_config('default', BaseWorld.strip_yml('conf/%s.yml' % config)[0])
    BaseWorld.apply_config('agents', BaseWorld.strip_yml('conf/agents.yml')[0])
    BaseWorld.apply_config('payloads', BaseWorld.strip_yml('conf/payloads.yml')[0])

    data_svc = DataService()
    contact_svc = ContactService()
    planning_svc = PlanningService()
    rest_svc = RestService()
    auth_svc = AuthService()
    file_svc = FileSvc()
    learning_svc = LearningService()
    event_svc = EventService()
    app_svc = AppService(application=web.Application())

    if args.fresh:
        asyncio.get_event_loop().run_until_complete(data_svc.destroy())
    run_tasks(services=app_svc.get_services())
