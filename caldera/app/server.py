import ssl
import socket
import os
import sys
import logging
import multiprocessing
import asyncio
import traceback
from datetime import datetime, timezone
import yaml
import functools

from aiohttp import web, WSCloseCode
import aiohttp_jinja2
from cryptography.fernet import Fernet

from .engine import database
from .engine.objects import SiteUser, ActiveConnection, Setting, AttackTechnique, Agent
from .updates import start_operations
from . import authentication as auth
from . import views
from . import api
from . import util
from . import attack


log = logging.getLogger(__name__)


def initialize_setting(settings, setting, message, default, arglist):
    write_settings = False 
    argval = None
    # check argv 
    argstring = '--' + '.'.join(setting)
    try:
        i = arglist.index(argstring)
        argval = arglist[i + 1]
    except (ValueError, IndexError):
        pass

    final = setting[-1]
    head = setting[:-1]
    v = settings
    for s in head:
        if s not in v or not isinstance(v[s], dict):
            write_settings = True
            v[s] = {}

        v = v[s]

    if argval:
        write_settings = True
        v[final] = argval
    elif final not in v:
        write_settings = True
        v[final] = default

    if write_settings:
        if '{}' in message:
            log.info(message.format(v[final]))
        else:
            log.info(message)

    return write_settings


def run(debug=False):
    default_conf_path = '../conf/settings.yaml.default'
    conf_file_path = '../conf/settings.yaml'
    crater_main_path = '../../dep/crater/crater/CraterMain.exe'
    abs_default_conf_path = util.relative_path(__file__, default_conf_path)
    abs_conf_file_path = util.relative_path(__file__, conf_file_path)
    abs_crater_main_path = util.relative_path(__file__, crater_main_path)
    default_db_host = 'localhost'
    default_db_port = 27017

    try:
        with open(abs_crater_main_path, 'r') as f:
            pass
    except FileNotFoundError:
        log.error("Could not find CraterMain.exe. Please place it at '{}'".format(os.path.abspath(abs_crater_main_path)))
        log.error("Or refer to the documentation for more information.")
        exit()

    try:
        with open(abs_conf_file_path, 'r') as f:
            settings = yaml.load(f.read())
    except FileNotFoundError:
        with open(abs_default_conf_path, 'r') as f:
            with open(abs_conf_file_path, 'w') as c_f:
                default = f.read()
                c_f.write(default)
                settings = yaml.load(default)

    # database key
    write_settings = False

    write_settings |= initialize_setting(settings, ('database', 'key'), "Creating private key for database", Fernet.generate_key(), [])
    write_settings |= initialize_setting(settings, ('database', 'host'), "Setting database host to '{}'", default_db_host, sys.argv)
    write_settings |= initialize_setting(settings, ('database', 'port'), "Initializing database port to '{}'", default_db_port, sys.argv)
    write_settings |= initialize_setting(settings, ('auth', 'key'), "Creating private authentication key", os.urandom(256), sys.argv)

    if write_settings:
        with open(abs_conf_file_path, 'w') as f:
            yaml.dump(settings, f, default_flow_style=False)

    # setup database key prior to fork
    database.initialize(settings['database']['key'], settings['database']['host'], settings['database']['port'])

    spawn_planner = True

    if spawn_planner:
        child = multiprocessing.Process(target=sigint_handler,
                                        args=(functools.partial(planner_process, settings['database']['host'],
                                                                settings['database']['port']),))
    else:
        child = multiprocessing.Process(target=sigint_handler,
                                        args=(functools.partial(web_process, settings, debug),))

    child.start()

    try:
        if spawn_planner:
            web_process(settings, debug)
        else:
            planner_process(settings['database']['host'], settings['database']['port'])
    except KeyboardInterrupt:
        log.info('Received CTRL+C signal. Quitting...')
    except Exception as e:
        log.error("{}\n{}".format(e, traceback.format_exc()))

    child.join(5)
    child.terminate()


async def heartbeat_init():
    try:
        while True:
            for agen in Agent.objects():
                if (datetime.now(timezone.utc) - agen.check_in).total_seconds() > 30:
                    agen.modify(**{'alive': False})
            # must be set to a low value to wakeup from KeyboardInterrupt
            # see python bug #23057: https://bugs.python.org/issue23057
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass


async def continual_sleep():
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass


async def websocket_shutdown(app):
    for ws in app['websockets']:
        await ws.close(code=WSCloseCode.GOING_AWAY,
                       message='Server shutdown')


def sigint_handler(target):
    try:
        target()
    except KeyboardInterrupt:
        pass


def web_process(settings, debug):
    logging.basicConfig(level=logging.DEBUG)

    if debug:
        asyncio.get_event_loop().set_debug(True)
        # loop.slow_callback_duration = 1000.0

    app = web.Application()
    app['websockets'] = []
    app.on_shutdown.append(websocket_shutdown)

    aiohttp_jinja2.setup(app, loader=aiohttp_jinja2.jinja2.FileSystemLoader('www/templates/'))

    views.init(app)
    api.init(app)

    host = settings['server']['host']
    port = settings['server']['port']

    # HTTPS settings (optional)
    if settings['server']['https']:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

        ssl_cmd = "openssl req -new -x509 -days 3652 -subj /CN='hostname --fqdn'/OU=Servers/O='hostname -d'/C=US -nodes -out {} -keyout {}".format(settings['crypto']['cert'], settings['crypto']['key'])
        if not os.path.isfile(settings['crypto']['cert']) and not os.path.isfile(settings['crypto']['key']):
            log.info("No SSL certificate or key found. Generating a self-signed SSL certificate for you.")
            os.system(ssl_cmd)
        elif not os.path.isfile(settings['crypto']['cert']):
            log.error("Found SSL key but no certificate. Please fix your configuration and try again.")
            return
        elif not os.path.isfile(settings['crypto']['key']):
            log.error("Found SSL certificate but no key. Please fix your configuration and try again.")
            return

        try:
            with open(settings['crypto']['cert'], 'r') as f:
                ssl_cert = f.read()
            views.cagent_conf = util.build_cagent_conf(socket.getfqdn().lower(), port, ssl_cert)
            ssl_context.load_cert_chain(settings['crypto']['cert'], settings['crypto']['key'])
        except FileNotFoundError:
            log.error("Could not locate certificate chain. Please generate with openssl and add to configuration file."
                      "\n\te.g. '{}'".format(ssl_cmd))
            return
        except ssl.SSLError as e:
            log.error("There was a problem creating the SSL context: '{}'.)".format(e.args))
            log.error("Are your SSL certificate and key correctly formatted?")
            return
    else:
        ssl_context = None

    # setup auth key
    auth.auth_key = settings['auth']['key']

    # quiet loud logging
    logging.getLogger('app.engine.database').setLevel(logging.INFO)
    logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

    database.start(settings['database']['host'], settings['database']['port'])

    if Setting.objects.count() < 1:
        Setting(recursion_limit=3).save()

    # setup Users
    try:
        for userdict in settings['users']:
            username = userdict['name']
            if not auth.username_exists(username):
                log.info("Creating new user: {}".format(username))

                auth.register_user(username, ['admin', 'human'], password=userdict['password'])
            user = SiteUser.objects.get(username=username)
            if 'admin' not in user.groups:
                user.modify(push__groups='admin')
    except KeyError:
        pass

    # remove all active connections
    for connection in ActiveConnection.objects:
        connection.delete()

    views.commit_id = util.git_commit_hash()
    if not views.commit_id:
        views.commit_id = ("Version could not be determined because either 'git' is not installed or the .git file "
                           "could not be found")

    handler = app.make_handler()

    loop = asyncio.get_event_loop()
    app_loop = loop.create_server(handler, host, port, ssl=ssl_context)
    heartbeat_task = loop.create_task(heartbeat_init())

    # Begin the event loop and run forever
    # May be exited without exception by simple Ctrl+C
    server = loop.run_until_complete(app_loop)

    log.info("Serving on " + ", ".join(["{}:{}".format(*_.getsockname()) for _ in server.sockets]))

    try:
        loop.run_forever()
    finally:
        log.info("Closing web server")
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.run_until_complete(app.shutdown())
        loop.run_until_complete(handler.shutdown(10.0))
        loop.run_until_complete(app.cleanup())
        heartbeat_task.cancel()
        loop.run_until_complete(heartbeat_task)
        loop.close()
        log.info("Web server closed")


def planner_process(host, port):
    # Log everything
    logging.basicConfig(level=logging.DEBUG)

    script_dir = os.path.dirname(__file__)
    abs_attack_path = os.path.join(script_dir, '../conf/attack_download.json')

    # quiet the database logging because it is loud
    logging.getLogger('app.engine.database').setLevel(logging.INFO)
    log.debug("Planner has started")
    database.start(host, port)

    # load default attack stuff if necessary
    rebuild_mappings = AttackTechnique.objects.count() == 0
    if rebuild_mappings:
        log.info("Loading default ATT&CK definitions")
        with open(abs_attack_path, 'r') as f:
            attack_mappings = f.read()
            attack.load_default(attack_mappings)

    loop = asyncio.get_event_loop()
    # workaround for python bug so we can catch KeyboardInterrupt: https://bugs.python.org/issue23057
    sleep_task = loop.create_task(continual_sleep())
    try:
        loop.run_until_complete(start_operations(rebuild_mappings))
    finally:
        sleep_task.cancel()
        loop.run_until_complete(sleep_task)
        loop.close()
        log.info("Planner closed")
