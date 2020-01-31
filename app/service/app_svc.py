import ast
import asyncio
import copy
import hashlib
import os
import json
import traceback
import uuid
from datetime import datetime, date
from importlib import import_module

import aiohttp_jinja2
import jinja2

from app.objects.c_adversary import Adversary
from app.objects.c_plugin import Plugin
from app.utility.base_service import BaseService


class AppService(BaseService):

    def __init__(self, application, config):
        self.application = application
        self.config = config
        self.log = self.add_service('app_svc', self)
        self.loop = asyncio.get_event_loop()

    async def start_sniffer_untrusted_agents(self):
        """
        Cyclic function that repeatedly checks if there are agents to be marked as untrusted

        :return: None
        """
        next_check = self.config['untrusted_timer']
        try:
            while True:
                await asyncio.sleep(next_check + 1)
                trusted_agents = await self.get_service('data_svc').locate('agents', match=dict(trusted=1))
                next_check = self.config['agent_config']['untrusted_timer']
                for a in trusted_agents:
                    silence_time = (datetime.now() - a.last_trusted_seen).total_seconds()
                    if silence_time > (self.config['agent_config']['untrusted_timer'] + int(a.sleep_max)):
                        self.log.debug('Agent (%s) now untrusted. Last seen %s sec ago' % (a.paw, int(silence_time)))
                        a.trusted = 0
                    else:
                        trust_time_left = self.config['agent_config']['untrusted_timer'] - silence_time
                        if trust_time_left < next_check:
                            next_check = trust_time_left
                await asyncio.sleep(15)
        except Exception:
            traceback.print_exc()

    async def find_link(self, unique):
        """
        Locate a given link by its unique property

        :param unique:
        :return:
        """
        for op in await self._services.get('data_svc').locate('operations'):
            exists = next((link for link in op.chain if link.unique == unique), None)
            if exists:
                return exists

    async def run_scheduler(self):
        """
        Kick off all scheduled jobs, as their schedule determines

        :return:
        """
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
                    self.loop.create_task(self.run_operation(sop))
            await asyncio.sleep(interval)

    async def resume_operations(self):
        """
        Resume all unfinished operations

        :return: None
        """
        await asyncio.sleep(10)
        for op in await self.get_service('data_svc').locate('operations', match=dict(finish=None)):
            self.loop.create_task(self.run_operation(op))

    async def run_operation(self, operation):
        try:
            self.log.debug('Starting operation: %s' % operation.name)
            planner = await self._get_planning_module(operation)
            operation.adversary = await self._adjust_adversary_phases(operation)

            for phase in operation.adversary.phases:
                if not await operation.is_closeable():
                    await self._update_operation(operation)
                    await planner.execute(phase)
                    if planner.stopping_condition_met:
                        break
                    await operation.wait_for_phase_completion()
                operation.phase = phase
            await self._cleanup_operation(operation)
            while not await operation.is_closeable():
                await asyncio.sleep(5)
                await self._update_operation(operation)
            await operation.close()
            await self._save_new_source(operation)
            self.log.debug('Completed operation: %s' % operation.name)
        except Exception:
            traceback.print_exc()

    async def load_plugins(self):
        """
        Store all plugins in the data store

        :return:
        """
        for plug in os.listdir('plugins'):
            if plug.startswith('.'):
                continue
            if not os.path.isdir('plugins/%s' % plug) or not os.path.isfile('plugins/%s/hook.py' % plug):
                self.log.error('Problem locating the "%s" plugin. Ensure CALDERA was cloned recursively.' % plug)
                exit(0)
            plugin = Plugin(name=plug)
            if await plugin.load():
                await self.get_service('data_svc').store(plugin)
                if plugin.name in self.config['plugins']:
                    plugin.enabled = True
        for plugin in self.config['plugins']:
            plug = await self._services.get('data_svc').locate('plugins', match=dict(name=plugin))
            [await p.enable(self.get_services()) for p in plug]
            self.log.debug('Enabling %s plugin' % plugin)

        templates = ['plugins/%s/templates' % p.name.lower()
                     for p in await self.get_service('data_svc').locate('plugins')]
        templates.append('templates')
        aiohttp_jinja2.setup(self.application, loader=jinja2.FileSystemLoader(templates))

    async def retrieve_compiled_file(self, name, platform):
        _, path = await self._services.get('file_svc').find_file_path('%s-%s' % (name, platform))
        signature = hashlib.md5(open(path, 'rb').read()).hexdigest()
        display_name = await self._services.get('contact_svc').build_filename(platform)
        self.log.debug('%s downloaded with hash=%s and name=%s' % (name, signature, display_name))
        return '%s-%s' % (name, platform), display_name

    async def teardown(self):
        await self._destroy_plugins()
        await self._services.get('data_svc').save_state()
        await self._write_reports()
        self.log.debug('[!] shutting down server...good-bye')

    """ PRIVATE """

    async def _destroy_plugins(self):
        for plugin in await self._services.get('data_svc').locate('plugins'):
            await plugin.destroy()

    async def _write_reports(self):
        file_svc = self.get_service('file_svc')
        r_dir = await file_svc.create_exfil_sub_directory('%s/reports' % self.config['reports_dir'])
        report = json.dumps(dict(self.get_service('contact_svc').report)).encode()
        await file_svc.save_file('contact_reports', report, r_dir)
        for op in self.get_service('data_svc').locate('operations'):
            await file_svc.save_file('operation_%s' % op.id,  json.dumps(op.report()).encode(), r_dir)

    async def _get_planning_module(self, operation):
        planning_module = import_module(operation.planner.module)
        planner_params = ast.literal_eval(operation.planner.params)
        return getattr(planning_module, 'LogicalPlanner')(operation,
                                                          self.get_service('planning_svc'), **planner_params,
                                                          stopping_conditions=operation.planner.stopping_conditions)

    async def _cleanup_operation(self, operation):
        for member in operation.agents:
            for link in await self.get_service('planning_svc').get_cleanup_links(operation, member):
                operation.add_link(link)
        await operation.wait_for_phase_completion()

    @staticmethod
    async def _adjust_adversary_phases(operation):
        """If an operation has phases disabled, replace operation
        adversary with new adversary whose phases are collapsed.
        Modified adversary is temporary and not stored, just used
        for the operation.
        """
        if not operation.phases_enabled:
            return Adversary(adversary_id=(operation.adversary.adversary_id + "_phases_disabled"),
                             name=(operation.adversary.name + " - with phases disabled"),
                             description=(operation.adversary.name + " with phases disabled"),
                             phases={1: [i for phase, ab in operation.adversary.phases.items() for i in ab]})
        else:
            return operation.adversary

    async def _save_new_source(self, operation):
        data = dict(
            id=str(uuid.uuid4()),
            name=operation.name,
            facts=[dict(trait=f.trait, value=f.value, score=f.score) for link in operation.chain for f in link.facts]
        )
        await self.get_service('rest_svc').persist_source(data)

    async def _update_operation(self, operation):
        operation.agents = await self.get_service('rest_svc').construct_agents_for_group(operation.group)
