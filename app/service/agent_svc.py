import asyncio
import json
import traceback
import typing
from datetime import datetime

from app.service.base_service import BaseService


class AgentService(BaseService):

    def __init__(self, untrusted_timer):
        self.log = self.add_service('agent_svc', self)
        self.loop = asyncio.get_event_loop()
        self.untrusted_timer = untrusted_timer

    async def start_sniffer_untrusted_agents(self):
        """
        Cyclic function that repeatedly checks if there are agents to be marked as untrusted
        :return: None
        """
        data_svc = self.get_service('data_svc')
        next_check = self.untrusted_timer
        try:
            while True:
                await asyncio.sleep(next_check+1)
                trusted_agents = await data_svc.explode_agents(criteria=dict(trusted=1))
                next_check = self.untrusted_timer
                for a in trusted_agents:
                    last_trusted_seen = datetime.strptime(a['last_trusted_seen'], '%Y-%m-%d %H:%M:%S')
                    silence_time = (datetime.now() - last_trusted_seen).total_seconds()
                    if silence_time > (self.untrusted_timer + a['sleep_max']):
                        await self.update_trust(a['paw'], 0)
                    else:
                        trust_time_left = self.untrusted_timer - silence_time
                        if trust_time_left < next_check:
                            next_check = trust_time_left
        except Exception:
            traceback.print_exc()

    async def update_trust(self, paw, trusted):
        """
        Set whether an agent should be trusted or not trusted
        :param paw:
        :param trusted:
        :return: None
        """
        data = dict(trusted=trusted)
        if trusted:
            data['last_trusted_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await self.get_service('data_svc').update('core_agent', 'paw', paw, data)
        self.log.debug('Agent %s is now trusted: %s' % (paw, bool(int(trusted))))

    async def handle_heartbeat(self, paw, platform, server, group, executors, architecture, location, pid, ppid, sleep):
        """
        Accept all components of an agent profile and save a new agent or register an updated heartbeat.
        :param paw:
        :param platform:
        :param server:
        :param group:
        :param executors:
        :param architecture:
        :param location:
        :param pid:
        :param ppid:
        :return: the agent object from explode_agents
        """
        self.log.debug('HEARTBEAT (%s)' % paw)
        agent = await self.get_service('data_svc').explode_agents(criteria=dict(paw=paw))
        now = self.get_current_timestamp()
        if agent:
            update_data = dict(last_seen=now, pid=pid, ppid=ppid)
            if agent[0]['trusted']:
                update_data['last_trusted_seen'] = now
            await self.get_service('data_svc').update('core_agent', 'paw', paw, data=update_data)
        else:
            queued = dict(last_seen=now, paw=paw, platform=platform, server=server, host_group=group,
                          location=location, architecture=architecture, pid=pid, ppid=ppid,
                          trusted=True, last_trusted_seen=now, sleep_min=sleep, sleep_max=sleep)
            await self.get_service('data_svc').create_agent(agent=queued, executors=executors)
            agent = await self.get_service('data_svc').explode_agents(criteria=dict(paw=paw))
        agent[0]['sleep'] = self.jitter('{}/{}'.format(agent[0]['sleep_min'], agent[0]['sleep_max']))
        return agent[0]

    async def get_instructions(self, paw):
        """
        Get next set of instructions to execute
        :param paw:
        :return: a list of links in JSON format
        """
        commands = await self.get_service('data_svc').explode_chain(criteria=dict(paw=paw))
        instructions = []
        for link in [c for c in commands if not c['collect'] and c['status'] == self.LinkState.EXECUTE.value]:
            await self.get_service('data_svc').update('core_chain', key='id', value=link['id'],
                                                      data=dict(collect=datetime.now()))
            payload = await self._gather_payload(link['ability'])
            instructions.append(json.dumps(dict(id=link['id'],
                                                sleep=link['jitter'],
                                                command=link['command'],
                                                executor=link['executor'],
                                                payload=payload)))
        return json.dumps(instructions)

    async def save_results(self, link_id, output, status):
        """
        Save the results from a single executed link
        :param link_id:
        :param output:
        :param status:
        :return: a JSON status message
        """
        await self.get_service('data_svc').create('core_result', dict(link_id=link_id, output=output))
        await self.get_service('data_svc').update('core_chain', key='id', value=link_id,
                                                  data=dict(status=int(status),
                                                            finish=self.get_current_timestamp()))
        link = await self.get_service('data_svc').explode_chain(criteria=dict(id=link_id))
        agent = (await self.get_service('data_svc').get('core_agent', dict(paw=link[0]['paw'])))[0]
        now = self.get_current_timestamp()
        update_data = dict(last_seen=now)
        if agent['trusted']:
            update_data['last_trusted_seen'] = now
        await self.get_service('data_svc').update('core_agent', 'paw', link[0]['paw'], data=update_data)
        return json.dumps(dict(status=True))

    async def perform_action(self, link: typing.Dict) -> int:
        """
        Perform a link in the context of an operation, respecting the 'run', 'paused' and 'run_one_step' operation
        states. Calling data_svc.create('core_chain', link) directly will schedule the link for execution,
        ignoring the state of the operation.
        :param link:
        :return: the id of the created link
        """
        data_svc = self.get_service('data_svc')
        operation_svc = self.get_service('operation_svc')
        op_id = link['op_id']

        operation = (await data_svc.dao.get('core_operation', dict(id=op_id)))[0]
        while operation['state'] != operation_svc.op_states['RUNNING']:
            if operation['state'] == operation_svc.op_states['RUN_ONE_LINK']:
                facts = link.pop('facts', None)
                link_id = await data_svc.create('core_chain', link)
                if facts:
                    await self._create_fact_link(facts, link_id, data_svc)
                await data_svc.dao.update('core_operation', 'id', op_id, dict(state=operation_svc.op_states['PAUSED']))
                return link_id
            else:
                await asyncio.sleep(30)
                operation = (await data_svc.dao.get('core_operation', dict(id=op_id)))[0]
        facts = link.pop('facts', None)
        link.pop('adversary_map_id')
        link_id = await data_svc.create('core_chain', link)
        if facts:
            await self._create_fact_link(facts, link_id, data_svc)
        return link_id

    """ PRIVATE """

    async def _create_fact_link(self, facts, link_id, data_svc):
        for fact in facts:
            await data_svc.create('core_link_fact', dict(link_id=link_id, fact_id=fact['id']))

    async def _gather_payload(self, ability_id):
        payload = await self.get_service('data_svc').get('core_payload', criteria=dict(ability=ability_id))
        return payload[0]['payload'] if payload else ''
