import argparse
import asyncio
import logging
import pathlib
import sys

import yaml
from aiohttp import web

from app.api.rest_api import RestApi
from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.contact_svc import ContactService
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService


def set_logging_state():
    logging.getLogger('aiohttp.access').setLevel(logging.FATAL)
    logging.getLogger('aiohttp_session').setLevel(logging.FATAL)
    logging.getLogger('aiohttp.server').setLevel(logging.FATAL)
    logging.getLogger('asyncio').setLevel(logging.FATAL)
    if cfg['debug']:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('aiohttp.server').setLevel(logging.DEBUG)
        logging.getLogger('asyncio').setLevel(logging.DEBUG)
    logging.debug('Agents will be considered untrusted after %s seconds of silence' % cfg['untrusted_timer'])
    logging.debug('Uploaded files will be put in %s' % cfg['exfil_dir'])
    logging.debug('Serving at http://%s:%s' % (cfg['host'], cfg['port']))


async def start_server(config, services):
    app = services.get('app_svc').application
    await auth_svc.apply(app, config['users'])

    app.router.add_route('*', '/file/download', services.get('file_svc').download)
    app.router.add_route('POST', '/file/upload', services.get('file_svc').upload_exfil)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, config['host'], config['port']).start()


def main(services, config):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(data_svc.restore_state())
    loop.run_until_complete(RestApi(services).enable())
    loop.run_until_complete(app_svc.load_plugins())
    loop.run_until_complete(data_svc.load_data(directory='data'))
    loop.create_task(app_svc.start_sniffer_untrusted_agents())
    loop.create_task(app_svc.resume_operations())
    loop.create_task(app_svc.run_scheduler())
    loop.run_until_complete(start_server(config, services))
    try:
        print('All systems ready. Navigate to http://%s:%s to log in.' % (config['host'], config['port']))
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(services.get('data_svc').save_state())
        logging.debug('[!] shutting down server...good-bye')


if __name__ == '__main__':
    sys.path.append('')
    parser = argparse.ArgumentParser('Welcome to the system')
    parser.add_argument('-E', '--environment', required=False, default='local', help='Select an env. file to use')
    parser.add_argument('--fresh', action='store_true', required=False, default=False,
                        help='remove object_store on start')
    args = parser.parse_args()
    config = args.environment if pathlib.Path('conf/%s.yml' % args.environment).exists() else 'default'
    with open('conf/%s.yml' % config) as c:
        cfg = yaml.load(c, Loader=yaml.FullLoader)
        set_logging_state()

        data_svc = DataService()
        contact_svc = ContactService()
        planning_svc = PlanningService()
        rest_svc = RestService()
        auth_svc = AuthService(cfg['api_key'])
        file_svc = FileSvc(cfg['exfil_dir'])
        app_svc = AppService(application=web.Application(), config=cfg)

        if args.fresh:
            asyncio.get_event_loop().run_until_complete(data_svc.destroy())
        main(config=cfg, services=app_svc.get_services())
