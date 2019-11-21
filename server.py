import argparse
import asyncio
import logging
import pathlib
import sys

import yaml
from aiohttp import web

from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.service.planning_svc import PlanningService


async def background_tasks(app):
    loop = asyncio.get_event_loop()
    loop.create_task(app_svc.start_sniffer_untrusted_agents())
    loop.create_task(app_svc.resume_operations())
    loop.create_task(app_svc.run_scheduler())
    loop.create_task(data_svc.load_data(directory='data'))
    loop.create_task(data_svc.restore_state())


async def init(app, address, port, services, users):
    await auth_svc.apply(app, users)
    app.on_startup.append(background_tasks)

    app.router.add_route('*', '/file/download', services.get('file_svc').download)
    app.router.add_route('POST', '/file/upload', services.get('file_svc').upload_exfil)

    await app_svc.load_plugins()
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, address, port).start()


def set_logging_state():
    state = logging.FATAL
    if cfg['debug']:
        state = logging.DEBUG
    logging.getLogger('aiohttp.access').setLevel(state)
    logging.getLogger('aiohttp_session').setLevel(state)
    logging.getLogger('aiohttp.server').setLevel(state)
    logging.getLogger('asyncio').setLevel(state)
    logging.getLogger().setLevel(state)


def main(app, services, host, port, users):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(app, host, port, services, users))
    try:
        print('All systems ready. Navigate to http://%s:%s to log in.' % (host, port))
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
        app = web.Application()

        data_svc = DataService()
        planning_svc = PlanningService()
        auth_svc = AuthService(cfg['api_key'])
        file_svc = FileSvc(cfg['exfil_dir'])
        app_svc = AppService(application=app, config=cfg)

        if args.fresh:
            asyncio.get_event_loop().run_until_complete(data_svc.reset())

        logging.debug('Agents will be considered untrusted after %s seconds of silence' % cfg['untrusted_timer'])
        logging.debug('Uploaded files will be put in %s' % cfg['exfil_dir'])
        logging.debug('Serving at http://%s:%s' % (cfg['host'], cfg['port']))
        main(app=app, services=app_svc.get_services(), host=cfg['host'], port=cfg['port'], users=cfg['users'])
