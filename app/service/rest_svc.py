import asyncio
import copy
import glob
import os
import pathlib
import uuid
from collections import defaultdict
from datetime import time

import yaml

from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_fact import Fact
from app.objects.c_link import Link
from app.objects.c_operation import Operation
from app.objects.c_schedule import Schedule
from app.utility.base_service import BaseService


class RestService(BaseService):

    def __init__(self):
        self.log = self.add_service('rest_svc', self)
        self.loop = asyncio.get_event_loop()

    async def persist_adversary(self, data):
        """
        Save a new adversary from either the GUI or REST API. This writes a new YML file into the core data/ directory.
        :param data:
        :return: the ID of the created adversary
        """
        i = data.pop('i')
        if not i:
            i = str(uuid.uuid4())
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % i, location='data')
        if not file_path:
            file_path = 'data/adversaries/%s.yml' % i
        with open(file_path, 'w+') as f:
            f.seek(0)
            p = defaultdict(list)
            for ability in data.pop('phases'):
                p[int(ability['phase'])].append(ability['id'])
            f.write(yaml.dump(dict(id=i, name=data.pop('name'), description=data.pop('description'), phases=dict(p))))
            f.truncate()
        for d in self.get_service('data_svc').data_dirs:
            await self.get_service('data_svc').load_data(d)
        return await self._poll_for_data('adversaries', dict(adversary_id=i))

    async def update_planner(self, data):
        """
        Update a new planner from either the GUI or REST API with new stopping conditions.
        This overwrites the existing YML file.
        :param data:
        :return: the ID of the created adversary
        """
        planner = (await self.get_service('data_svc').locate('planners', dict(name=data['name'])))[0]
        planner_id = planner.planner_id
        file_path = await self._get_file_path(planner_id)
        planner_dict = await self._read_from_yaml(file_path)
        planner_dict['stopping_conditions'] = self._get_stopping_conditions(data)
        await self._write_to_yaml(file_path, planner_dict)
        planner.stopping_conditions = [Fact(trait=f.get('trait'), value=f.get('value'))
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
        for d in self.get_service('data_svc').data_dirs:
            await self.get_service('data_svc').load_data(d)
        return await self._poll_for_data('abilities', dict(ability_id=data.get('id')))

    async def persist_source(self, data):
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % data.get('id'), location='data')
        if not file_path:
            file_path = 'data/facts/%s.yml' % data.get('id')
        with open(file_path, 'w+') as f:
            f.seek(0)
            f.write(yaml.dump(data))
        for d in self.get_service('data_svc').data_dirs:
            await self.get_service('data_svc').load_data(d)
        return await self._poll_for_data('sources', dict(id=data.get('id')))

    async def delete_agent(self, data):
        await self.get_service('data_svc').remove('agents', data)
        return 'Delete action completed'

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
        return [o.display for o in await self.get_service('data_svc').locate(object_name, match=data)]

    async def display_result(self, data):
        link_id = data.pop('link_id')
        link = await self.get_service('app_svc').find_link(link_id)
        if link:
            try:
                _, content = await self.get_service('file_svc').read_file(name='%s' % link_id, location='data/results')
                return dict(link=link.display, output=content.decode('utf-8'))
            except FileNotFoundError:
                return ''
        return ''

    async def display_operation_report(self, data):
        op_id = data.pop('op_id')
        op = (await self.get_service('data_svc').locate('operations', match=dict(id=int(op_id))))[0]
        return op.report

    async def update_agent_data(self, data):
        agent = await self.get_service('data_svc').store(Agent(paw=data.pop('paw'), group=data.get('group'),
                                                               trusted=data.get('trusted'),
                                                               sleep_min=data.get('sleep_min'),
                                                               sleep_max=data.get('sleep_max')))
        return agent.display

    async def update_chain_data(self, data):
        link = await self.get_service('app_svc').find_link(data.pop('link_id'))
        link.status = data.get('status')
        if data.get('command'):
            link.command = data.get('command')
        return ''

    async def create_operation(self, data):
        operation = await self._build_operation_object(data)
        operation.set_start_details()
        await self.get_service('data_svc').store(operation)
        self.loop.create_task(self.get_service('app_svc').run_operation(operation))
        return [operation.display]

    async def create_schedule(self, data):
        operation = await self._build_operation_object(data['operation'])
        scheduled = await self.get_service('data_svc').store(
            Schedule(name=operation.name,
                     schedule=time(data['schedule']['hour'], data['schedule']['minute'], 0),
                     task=operation)
        )
        self.log.debug('Scheduled new operation (%s) for %s' % (operation.name, scheduled.schedule))

    async def list_payloads(self):
        payload_dirs = [pathlib.Path.cwd() / 'data' / 'payloads']
        payload_dirs.extend(pathlib.Path.cwd() / 'plugins' / plugin.name / 'payloads'
                            for plugin in await self.get_service('data_svc').locate('plugins'))
        return set(p.name for p_dir in payload_dirs for p in p_dir.glob('*')
                   if p.is_file() and not p.name.startswith('.'))

    async def get_potential_links(self, op_id, paw):
        operation = (await self.get_service('data_svc').locate('operations', match=dict(id=op_id)))[0]
        if operation.finish:
            return []
        agents = await self.get_service('data_svc').locate('agents', match=dict(paw=paw))
        potential_abilities = await self._build_potential_abilities(operation)
        return await self._build_potential_links(operation, agents, potential_abilities)

    async def apply_potential_link(self, l):
        link = Link.from_json(l)
        operation = (await self.get_service('data_svc').locate('operations', match=dict(id=link.operation)))[0]
        await operation.apply(link)

    async def change_operation_state(self, op_id, state):
        operation = await self.get_service('data_svc').locate('operations', match=dict(id=op_id))
        operation[0].state = state
        self.log.debug('changing operation=%s state to %s' % (op_id, state))

    async def get_link_pin(self, json_data):
        link = await self.get_service('app_svc').find_link(json_data['link'])
        if link and link.collect and not link.finish:
            return link.pin
        return 'Invalid'

    """ PRIVATE """

    async def _build_operation_object(self, data):
        name = data.pop('name')
        group = data.pop('group')
        planner = await self.get_service('data_svc').locate('planners', match=dict(name=data.pop('planner')))
        adversary = await self._construct_adversary_for_op(data.pop('adversary_id'))
        agents = await self._construct_agents_for_group(group)
        sources = await self.get_service('data_svc').locate('sources', match=dict(name=data.pop('source')))

        return Operation(name=name, planner=planner[0], agents=agents, adversary=adversary, group=group,
                         jitter=data.pop('jitter'), source=next(iter(sources), None), state=data.pop('state'),
                         allow_untrusted=int(data.pop('allow_untrusted')), autonomous=int(data.pop('autonomous')),
                         phases_enabled=bool(int(data.pop('phases_enabled'))), obfuscator=data.pop('obfuscator'),
                         max_time=int(data.pop('max_time')))

    async def _poll_for_data(self, collection, search):
        coll, checks = 0, 0
        while not coll or checks == 5:
            coll = await self.get_service('data_svc').locate(collection, match=search)
            await asyncio.sleep(1)
            checks += 1
        return [c.display for c in coll]

    @staticmethod
    async def _read_from_yaml(file_path):
        with open(file_path, 'r') as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)

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
        for a in await self.get_service('data_svc').locate('abilities'):
            if not operation.adversary.has_ability(a):
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
        return Adversary(adversary_id=0, name='ad-hoc', description='an empty adversary profile', phases={'1': []})

    async def _construct_agents_for_group(self, group):
        if group:
            return await self.get_service('data_svc').locate('agents', match=dict(group=group))
        return await self.get_service('data_svc').locate('agents')
