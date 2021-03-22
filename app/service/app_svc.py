import asyncio
import copy
import glob
import hashlib
import json
import os
import time
from collections import namedtuple
from datetime import datetime, date
from importlib import import_module

import aiohttp_jinja2
import jinja2
import yaml
from aiohttp import web

from app.objects.c_plugin import Plugin
from app.service.interfaces.i_app_svc import AppServiceInterface
from app.utility.base_service import BaseService

Error = namedtuple('Error', ['name', 'msg'])


class AppService(AppServiceInterface, BaseService):

    @property
    def errors(self):
        return [dict(e._asdict()) for e in self._errors]

    def __init__(self, application):
        self.application = application
        self.log = self.add_service('app_svc', self)
        self.loop = asyncio.get_event_loop()
        self._errors = []
        self._loaded_plugins = []  # all plugins that were loaded, including disabled ones

    async def start_sniffer_untrusted_agents(self):
        next_check = self.get_config(name='agents', prop='untrusted_timer')
        try:
            while True:
                await asyncio.sleep(next_check + 1)
                trusted_agents = await self.get_service('data_svc').locate('agents', match=dict(trusted=1))
                next_check = self.get_config(name='agents', prop='untrusted_timer')
                for a in trusted_agents:
                    silence_time = (datetime.now() - a.last_trusted_seen).total_seconds()
                    if silence_time > (self.get_config(name='agents', prop='untrusted_timer') + int(a.sleep_max)):
                        self.log.debug('Agent (%s) now untrusted. Last seen %s sec ago' % (a.paw, int(silence_time)))
                        a.trusted = 0
                    else:
                        trust_time_left = self.get_config(name='agents', prop='untrusted_timer') - silence_time
                        if trust_time_left < next_check:
                            next_check = trust_time_left
                await asyncio.sleep(15)
        except Exception as e:
            self.log.error(repr(e), exc_info=True)

    async def find_link(self, unique):
        operations = await self.get_service('data_svc').locate('operations')
        agents = await self.get_service('data_svc').locate('agents')
        return self._check_links_for_match(unique, [op.chain for op in operations] + [a.links for a in agents])

    async def find_op_with_link(self, link_id):
        """
        Retrieves the operation that a link_id belongs to. Will search currently running
        operations first.
        """
        operations = await self.get_service('data_svc').locate('operations', match=dict(state='running'))
        op = next((o for o in operations if o.has_link(link_id)), None)
        if not op:
            operations = await self.get_service('data_svc').locate('operations', match=dict())
            op = next((o for o in operations if o.has_link(link_id)), None)
        return op

    async def run_scheduler(self):
        while True:
            interval = 60
            for s in await self.get_service('data_svc').locate('schedules'):
                now = datetime.now().time()
                diff = datetime.combine(date.today(), now) - datetime.combine(date.today(), s.schedule)
                if interval > diff.total_seconds() > 0:
                    self.log.debug('Pulling %s off the scheduler' % s.name)
                    sop = copy.deepcopy(s.task)
                    sop.set_start_details()
                    await self._services.get('data_svc').store(sop)
                    self.loop.create_task(sop.run(self.get_services()))
            await asyncio.sleep(interval)

    async def resume_operations(self):
        await asyncio.sleep(10)
        for op in await self.get_service('data_svc').locate('operations', match=dict(finish=None)):
            self.loop.create_task(op.run(self.get_services()))

    async def load_plugins(self, plugins):
        def trim(p):
            if p.startswith('.'):
                return False
            return True

        async def load(p):
            plugin = Plugin(name=p)
            if plugin.load_plugin():
                await self.get_service('data_svc').store(plugin)
                self._loaded_plugins.append(plugin)

            if plugin.name in self.get_config('plugins'):
                await plugin.enable(self.get_services())
                self.log.info('Enabled plugin: %s' % plugin.name)

        for plug in filter(trim, plugins):
            if not os.path.isdir('plugins/%s' % plug) or not os.path.isfile('plugins/%s/hook.py' % plug):
                self.log.error('Problem locating the "%s" plugin. Ensure code base was cloned recursively.' % plug)
                exit(0)
            asyncio.get_event_loop().create_task(load(plug))

        templates = ['plugins/%s/templates' % p.lower() for p in self.get_config('plugins')]
        templates.append('templates')
        aiohttp_jinja2.setup(self.application, loader=jinja2.FileSystemLoader(templates))

    async def retrieve_compiled_file(self, name, platform):
        _, path = await self._services.get('file_svc').find_file_path('%s-%s' % (name, platform))
        signature = hashlib.sha256(open(path, 'rb').read()).hexdigest()
        display_name = await self._services.get('contact_svc').build_filename()
        self.log.debug('%s downloaded with hash=%s and name=%s' % (name, signature, display_name))
        return '%s-%s' % (name, platform), display_name

    async def teardown(self, main_config_file='default'):
        await self._destroy_plugins()
        await self._save_configurations(main_config_file=main_config_file)
        await self._services.get('data_svc').save_state()
        await self._write_reports()
        self.log.debug('[!] shutting down server...good-bye')

    async def register_contacts(self):
        contact_svc = self.get_service('contact_svc')
        for contact_file in glob.iglob('app/contacts/*.py'):
            contact_module_name = contact_file.replace('/', '.').replace('\\', '.').replace('.py', '')
            contact_class = import_module(contact_module_name).Contact
            await contact_svc.register(contact_class(self.get_services()))

    async def validate_requirement(self, requirement, params):
        if not self.check_requirement(params):
            msg = '%s does not meet the minimum version of %s' % (requirement, params['version'])
            if params.get('optional', False):
                msg = '. '.join([
                    msg,
                    '%s is an optional dependency and its absence will not affect Caldera\'s core operation' % requirement.capitalize(),
                    params.get('reason', '')
                ])
                self.log.warning(msg)
            else:
                self.log.error(msg)
            self._errors.append(Error('requirement', '%s version needs to be >= %s' % (requirement, params['version'])))
            return False
        return True

    async def validate_requirements(self):
        for requirement, params in self.get_config('requirements').items():
            await self.validate_requirement(requirement, params)

    async def load_plugin_expansions(self, plugins=()):
        for p in plugins:
            await p.expand(services=self.get_services())

    async def watch_ability_files(self):
        await asyncio.sleep(int(self.get_config('ability_refresh')))
        plugins = [p for p in await self.get_service('data_svc').locate('plugins', dict(enabled=True)) if p.data_dir]
        plugins.append(Plugin(data_dir='data'))
        while True:
            for p in plugins:
                files = (os.path.join(rt, fle) for rt, _, f in os.walk(p.data_dir+'/abilities') for fle in f if
                         time.time() - os.stat(os.path.join(rt, fle)).st_mtime < int(self.get_config('ability_refresh')))
                for f in files:
                    self.log.debug('[%s] Reloading %s' % (p.name, f))
                    await self.get_service('data_svc').load_ability_file(filename=f, access=p.access)
            await asyncio.sleep(int(self.get_config('ability_refresh')))

    def register_subapp(self, path: str,  app: web.Application):
        """Registers a web application under the root application.

        Requests under `path` will be routed to this app.
        """
        self.application.add_subapp(path, app)

    def get_loaded_plugins(self):
        return tuple(self._loaded_plugins)

    """ PRIVATE """

    async def _save_configurations(self, main_config_file='default'):
        for cfg_name, cfg_file in [('main', main_config_file), ('agents', 'agents'), ('payloads', 'payloads')]:
            with open('conf/%s.yml' % cfg_file, 'w') as config:
                config.write(yaml.dump(self.get_config(name=cfg_name)))

    async def _destroy_plugins(self):
        for plugin in await self._services.get('data_svc').locate('plugins', dict(enabled=True)):
            await plugin.destroy(self.get_services())

    async def _write_reports(self):
        file_svc = self.get_service('file_svc')
        r_dir = await file_svc.create_exfil_sub_directory('%s/reports' % self.get_config('reports_dir'))
        report = json.dumps(dict(self.get_service('contact_svc').report)).encode()
        await file_svc.save_file('contact_reports', report, r_dir)
        for op in await self.get_service('data_svc').locate('operations'):
            report = json.dumps(await op.report(self.get_service('file_svc'), self.get_service('data_svc')))
            if report:
                await file_svc.save_file('operation_%s' % op.id, report.encode(), r_dir)

    @staticmethod
    def _check_links_for_match(unique, links):
        for ll in links:
            exists = next((link for link in ll if link.unique == str(unique)), None)
            if exists:
                return exists
