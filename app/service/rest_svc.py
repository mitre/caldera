import asyncio
import copy
import glob
import os
import pathlib
import uuid
from datetime import time, datetime

import yaml
from aiohttp import web

from app.objects.c_adversary import Adversary
from app.objects.c_operation import Operation
from app.objects.c_schedule import Schedule
from app.objects.secondclass.c_fact import Fact
from app.service.interfaces.i_rest_svc import RestServiceInterface
from app.utility.base_service import BaseService


class RestService(RestServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('rest_svc', self)
        self.loop = asyncio.get_event_loop()

    async def persist_adversary(self, data):
        i = data.pop('i')
        if not i:
            i = str(uuid.uuid4())
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % i, location='data')
        if not file_path:
            file_path = 'data/adversaries/%s.yml' % i
        with open(file_path, 'w+') as f:
            f.seek(0)
            p = list()
            for ability in data.pop('atomic_ordering'):
                p.append(ability['id'])
            f.write(yaml.dump(dict(id=i, name=data.pop('name'), description=data.pop('description'),
                                   atomic_ordering=p)))
            f.truncate()
        await self._services.get('data_svc').reload_data()
        return [a.display for a in await self._services.get('data_svc').locate('adversaries', dict(adversary_id=i))]

    async def update_planner(self, data):
        planner = (await self.get_service('data_svc').locate('planners', dict(name=data['name'])))[0]
        planner_id = planner.planner_id
        file_path = await self._get_file_path(planner_id)
        planner_dict = await self._read_from_yaml(file_path)
        planner_dict['stopping_conditions'] = self._get_stopping_conditions(data)
        await self._write_to_yaml(file_path, planner_dict)
        planner.stopping_conditions = [Fact.load(dict(trait=f.get('trait'), value=f.get('value')))
                                       for f in data['stopping_conditions']]
        await self.get_service('data_svc').store(planner)

    async def persist_ability(self, data):
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % data.get('id'), location='data')
        if not file_path:
            d = 'data/abilities/%s' % data.get('tactic')
            if not os.path.exists(d):
                os.makedirs(d)
            file_path = '%s/%s.yml' % (d, data.get('id'))
        with open(file_path, 'w+') as f:
            f.seek(0)
            f.write(yaml.dump([data]))
        await self.get_service('data_svc').remove('abilities', dict(ability_id=data.get('id')))
        await self.get_service('data_svc').reload_data()
        return [a.display for a in await self.get_service('data_svc').locate('abilities', dict(ability_id=data.get('id')))]

    async def persist_source(self, data):
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % data.get('id'), location='data')
        if not file_path:
            file_path = 'data/sources/%s.yml' % data.get('id')
        with open(file_path, 'w+') as f:
            f.seek(0)
            f.write(yaml.dump(data))
        await self._services.get('data_svc').reload_data()
        return [s.display for s in await self._services.get('data_svc').locate('sources', dict(id=data.get('id')))]

    async def delete_agent(self, data):
        await self.get_service('data_svc').remove('agents', data)
        return 'Delete action completed'

    async def delete_ability(self, data):
        return await self._delete_data_from_memory_and_disk(ram_key='abilities', identifier='ability_id', data=data)

    async def delete_adversary(self, data):
        return await self._delete_data_from_memory_and_disk(ram_key='adversaries', identifier='adversary_id', data=data)

    async def delete_operation(self, data):
        await self.get_service('data_svc').remove('operations', data)
        await self.get_service('data_svc').remove('sources', dict(id=str(data.get('id'))))
        for f in glob.glob('data/results/*'):
            if '%s-' % data.get('id') in f:
                os.remove(f)
        for f in glob.glob('data/facts/*.yml'):
            if '%s' % data.get('id') in f:
                os.remove(f)
        return 'Delete action completed'

    async def display_objects(self, object_name, data):
        results = [o.display for o in await self.get_service('data_svc').locate(object_name, match=data)]
        return await self._explode_display_results(object_name, results)

    async def display_result(self, data):
        link_id = str(data.pop('link_id'))
        link = await self.get_service('app_svc').find_link(link_id)
        if link:
            try:
                content = self.get_service('file_svc').read_result_file('%s' % link_id)
                return dict(link=link.display, output=content)
            except FileNotFoundError:
                return ''
        return ''

    async def display_operation_report(self, data):
        op_id = data.pop('op_id')
        op = (await self.get_service('data_svc').locate('operations', match=dict(id=int(op_id))))[0]
        return await op.report(file_svc=self.get_service('file_svc'), data_svc=self.get_service('data_svc'),
                               output=data.get('agent_output'))

    async def download_contact_report(self, contact):
        return dict(contacts=self.get_service('contact_svc').report.get(contact.get('contact'), dict()))

    async def update_agent_data(self, data):
        paw = data.pop('paw', None)
        if paw is None:
            await self._update_global_props(**data)
        for agent in await self.get_service('data_svc').locate('agents', match=dict(paw=paw)):
            await agent.gui_modification(**data)
            return agent.display

    async def update_chain_data(self, data):
        link = await self.get_service('app_svc').find_link(data.pop('link_id'))
        link.status = data.get('status')
        if data.get('command'):
            link.command = data.get('command')
        return ''

    async def create_operation(self, access, data):
        operation = await self._build_operation_object(access, data)
        operation.set_start_details()
        await self.get_service('data_svc').store(operation)
        self.loop.create_task(operation.run(self.get_services()))
        return [operation.display]

    async def create_schedule(self, access, data):
        operation = await self._build_operation_object(access, data['operation'])
        scheduled = await self.get_service('data_svc').store(
            Schedule(name=operation.name,
                     schedule=time(data['schedule']['hour'], data['schedule']['minute'], 0),
                     task=operation)
        )
        self.log.debug('Scheduled new operation (%s) for %s' % (operation.name, scheduled.schedule))

    async def list_payloads(self):
        payload_dirs = [pathlib.Path.cwd() / 'data' / 'payloads']
        payload_dirs.extend(pathlib.Path.cwd() / 'plugins' / plugin.name / 'payloads'
                            for plugin in await self.get_service('data_svc').locate('plugins') if plugin.enabled)
        return set(p.name for p_dir in payload_dirs for p in p_dir.glob('*')
                   if p.is_file() and not p.name.startswith('.'))

    async def find_abilities(self, paw):
        data_svc = self.get_service('data_svc')
        agent = (await data_svc.locate('agents', match=dict(paw=paw)))[0]
        return await agent.capabilities(await self.get_service('data_svc').locate('abilities'))

    async def get_potential_links(self, op_id, paw=None):
        operation = (await self.get_service('data_svc').locate('operations', match=dict(id=op_id)))[0]
        if operation.finish:
            return []
        agents = await self.get_service('data_svc').locate('agents', match=dict(paw=paw)) if paw else operation.agents
        potential_abilities = await self._build_potential_abilities(operation)
        operation.potential_links = await self._build_potential_links(operation, agents, potential_abilities)
        return dict(links=[l.display for l in operation.potential_links])

    async def apply_potential_link(self, link):
        operation = await self.get_service('app_svc').find_op_with_link(link.id)
        return await operation.apply(link)

    async def task_agent_with_ability(self, paw, ability_id, obfuscator, facts=()):
        new_links = []
        for agent in await self.get_service('data_svc').locate('agents', dict(paw=paw)):
            self.log.debug('Tasking %s with %s' % (paw, ability_id))
            links = await agent.task(
                abilities=await self.get_service('data_svc').locate('abilities', match=dict(ability_id=ability_id)),
                obfuscator=obfuscator,
                facts=facts
            )
            new_links.extend(links)
        return new_links

    async def get_link_pin(self, json_data):
        link = await self.get_service('app_svc').find_link(json_data['link'])
        if link and link.collect and not link.finish:
            return link.pin
        return 0

    async def construct_agents_for_group(self, group):
        if group:
            return await self.get_service('data_svc').locate('agents', match=dict(group=group))
        return await self.get_service('data_svc').locate('agents')

    async def update_config(self, data):
        if data.get('prop') == 'plugin':
            enabled_plugins = self.get_config('plugins')
            enabled_plugins.append(data.get('value'))
        else:
            self.set_config('main', data.get('prop'), data.get('value'))
        return self.get_config()

    async def update_operation(self, op_id, state=None, autonomous=None, obfuscator=None):
        async def validate(op):
            try:
                if not len(op):
                    raise web.HTTPNotFound
                elif await op[0].is_finished():
                    raise web.HTTPBadRequest(body='This operation has already finished.')
                elif state not in op[0].states.values():
                    raise web.HTTPBadRequest(body='state must be one of {}'.format(op[0].states.values()))
            except Exception as e:
                self.log.error(repr(e))
        operation = await self.get_service('data_svc').locate('operations', match=dict(id=op_id))
        if state:
            await validate(operation)
            operation[0].state = state
            operation[0].finish = datetime.now()
            self.log.debug('Changing operation=%s state to %s' % (op_id, state))
        if autonomous:
            operation[0].autonomous = 0 if operation[0].autonomous else 1
            self.log.debug('Toggled operation=%s autonomous to %s' % (op_id, bool(operation[0].autonomous)))
        if obfuscator:
            operation[0].obfuscator = obfuscator
            self.log.debug('Updated operation=%s obfuscator to %s' % (op_id, operation[0].obfuscator))

    """ PRIVATE """

    async def _build_operation_object(self, access, data):
        name = data.pop('name')
        group = data.pop('group', '')
        planner = await self.get_service('data_svc').locate('planners', match=dict(name=data.get('planner', 'atomic')))
        adversary = await self._construct_adversary_for_op(data.pop('adversary_id', ''))
        agents = await self.construct_agents_for_group(group)
        sources = await self.get_service('data_svc').locate('sources', match=dict(name=data.pop('source', 'basic')))
        allowed = self.Access.BLUE if self.Access.BLUE in access['access'] else self.Access.RED

        return Operation(name=name, planner=planner[0], agents=agents, adversary=adversary,
                         group=group, jitter=data.pop('jitter', '2/8'), source=next(iter(sources), None),
                         state=data.pop('state', 'running'), autonomous=int(data.pop('autonomous', 1)), access=allowed,
                         obfuscator=data.pop('obfuscator', 'plain-text'),
                         auto_close=bool(int(data.pop('auto_close', 0))), visibility=int(data.pop('visibility', '50')))

    @staticmethod
    async def _read_from_yaml(file_path):
        with open(file_path, 'r') as f:
            return yaml.safe_load(f.read())

    @staticmethod
    async def _write_to_yaml(file_path, content):
        with open(file_path, 'w') as f:
            f.write(yaml.dump(content))

    async def _get_file_path(self, planner_id):
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % planner_id, location='data')
        if not file_path:
            file_path = 'data/planners/%s.yml' % planner_id
        return file_path

    @staticmethod
    def _get_stopping_conditions(data):
        new_stopping_conditions = data.get('stopping_conditions')
        if new_stopping_conditions:
            return [{s.get('trait'): s.get('value')} for s in new_stopping_conditions]

    async def _build_potential_abilities(self, operation):
        potential_abilities = []
        for a in await self.get_service('data_svc').locate('abilities', match=dict(access=operation.access)):
            if not operation.adversary.has_ability(a.ability_id):
                potential_abilities.append(a)
        return potential_abilities

    async def _build_potential_links(self, operation, agents, abilities):
        potential_links = []
        for a in agents:
            for pl in await self.get_service('planning_svc').generate_and_trim_links(a, operation, abilities):
                potential_links.append(pl)
        return await self.get_service('planning_svc').sort_links(potential_links)

    async def _construct_adversary_for_op(self, adversary_id):
        adv = await self.get_service('data_svc').locate('adversaries', match=dict(adversary_id=adversary_id))
        if adv:
            return copy.deepcopy(adv[0])
        return Adversary.load(dict(adversary_id='ad-hoc', name='ad-hoc', description='an empty adversary profile', atomic_ordering=[]))

    async def _update_global_props(self, sleep_min, sleep_max, watchdog, untrusted, implant_name, bootstrap_abilities):
        if implant_name:
            self.set_config(name='agents', prop='implant_name', value=implant_name)
        if bootstrap_abilities:
            abilities = self.get_config(name='agents', prop='bootstrap_abilities')
            abilities.append(bootstrap_abilities)
        self.set_config(name='agents', prop='sleep_min', value=sleep_min)
        self.set_config(name='agents', prop='sleep_max', value=sleep_max)
        self.set_config(name='agents', prop='untrusted_timer', value=untrusted)
        self.set_config(name='agents', prop='watchdog', value=watchdog)

    async def _explode_display_results(self, object_name, results):
        if object_name == 'adversaries':
            for adv in results:
                adv['atomic_ordering'] = [ab.display for ab_id in adv['atomic_ordering'] for ab in
                                          await self.get_service('data_svc').locate('abilities',
                                                                                    match=dict(ability_id=ab_id))]
        return results

    async def _delete_data_from_memory_and_disk(self, ram_key, identifier, data):
        await self.get_service('data_svc').remove(ram_key, data)
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % data.get(identifier),
                                                                         location='data')
        if not file_path:
            file_path = 'data/%s/%s.yml' % (ram_key, data.get(identifier))
        if os.path.exists(file_path):
            os.remove(file_path)
        return 'Delete action completed'
