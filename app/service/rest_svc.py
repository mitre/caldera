import asyncio
import glob
import os
import pathlib
from collections import defaultdict
from datetime import time

import yaml

from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.c_fact import Fact
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
        id = planner.id
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % id, location='data')
        if not file_path:
            file_path = 'data/planners/%s.yml' % id
        with open(file_path, 'r') as f:
            planner_obj = yaml.load(f.read(), Loader=yaml.FullLoader)
        sc = data.get('stopping_conditions')
        if sc:
            sc = [{s.get('trait'): s.get('value')} for s in sc]
        planner_obj['stopping_conditions'] = sc
        with open(file_path, 'w') as f:
            f.write(yaml.dump(planner_obj))
        planner.stopping_conditions = [Fact(trait=f.get('trait'), value=f.get('value'))
                                       for f in data['stopping_conditions']]
        await self.get_service('data_svc').remove('planners', dict(name=data['name']))
        await self.get_service('data_svc').store(planner)
        return

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

    """ PRIVATE """

    async def _build_operation_object(self, data):
        name = data.pop('name')
        planner = await self.get_service('data_svc').locate('planners', match=dict(name=data.pop('planner')))
        adversary = await self.get_service('data_svc').locate('adversaries',
                                                              match=dict(adversary_id=data.pop('adversary_id')))
        agents = await self.get_service('data_svc').locate('agents', match=dict(group=data.pop('group')))
        sources = await self.get_service('data_svc').locate('sources', match=dict(name=data.pop('source')))
        return Operation(name=name, planner=planner[0], agents=agents, adversary=adversary[0],
                         jitter=data.pop('jitter'), source=next(iter(sources), None), state=data.pop('state'),
                         allow_untrusted=int(data.pop('allow_untrusted')), autonomous=int(data.pop('autonomous')),
                         phases_enabled=bool(int(data.pop('phases_enabled'))),
                         obfuscator=data.pop('obfuscator'))

    async def _poll_for_data(self, collection, search):
        coll, checks = 0, 0
        while not coll or checks == 5:
            coll = await self.get_service('data_svc').locate(collection, match=search)
            await asyncio.sleep(1)
            checks += 1
        return [c.display for c in coll]
