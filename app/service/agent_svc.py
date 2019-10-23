import asyncio
import json
import traceback
import typing
from datetime import datetime

from app.service.base_service import BaseService


class AgentService(BaseService):

    def __init__(self, untrusted_timer):
        self.log = self.add_service('agent_svc', self)
        self.data_svc = self.get_service('data_svc')
        self.loop = asyncio.get_event_loop()
        self.untrusted_timer = untrusted_timer

    async def start_sniffer_untrusted_agents(self):
        """
        Cyclic function that repeatedly checks if there are agents to be marked as untrusted
        :return: None
        """
        next_check = self.untrusted_timer
        try:
            while True:
                await asyncio.sleep(next_check+1)
                trusted_agents = await self.data_svc.explode('agent', criteria=dict(trusted=1))
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
        await self.data_svc.update('agent', 'paw', paw, data)
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
        :return: the agent object from explode
        """
        self.log.debug('HEARTBEAT (%s)' % paw)
        agent = await self.data_svc.explode('agent', criteria=dict(paw=paw))
        now = self.get_current_timestamp()
        if agent:
            update_data = dict(last_seen=now, pid=pid, ppid=ppid)
            if agent[0]['trusted']:
                update_data['last_trusted_seen'] = now
            await self.data_svc.update('agent', 'paw', paw, data=update_data)
            await self._update_agent_executor(agent[0]['id'], executors, agent[0]['executors'])
        else:
            queued = dict(last_seen=now, paw=paw, platform=platform, server=server, host_group=group,
                          location=location, architecture=architecture, pid=pid, ppid=ppid,
                          trusted=True, last_trusted_seen=now, sleep_min=sleep, sleep_max=sleep)
            await self.data_svc.save('agent', dict(agent=queued, executors=executors))
            agent = await self.data_svc.explode('agent', criteria=dict(paw=paw))
        agent[0]['sleep'] = self.jitter('{}/{}'.format(agent[0]['sleep_min'], agent[0]['sleep_max']))
        return agent[0]

    async def get_instructions(self, paw):
        """
        Get next set of instructions to execute
        :param paw:
        :return: a list of links in JSON format
        """
        commands = await self.data_svc.explode('chain', criteria=dict(paw=paw))
        instructions = []
        for link in [c for c in commands if not c['collect'] and c['status'] == self.LinkState.EXECUTE.value]:
            await self.data_svc.update('chain', key='id', value=link['id'], data=dict(collect=datetime.now()))
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
        await self.data_svc.save('result', dict(link_id=link_id, output=output))
        await self.data_svc.update('chain', key='id', value=link_id, data=dict(status=int(status),
                                                                                    finish=self.get_current_timestamp()))
        link = await self.data_svc.explode('chain', criteria=dict(id=link_id))
        agent = (await self.data_svc.get('agent', dict(paw=link[0]['paw'])))[0]
        now = self.get_current_timestamp()
        update_data = dict(last_seen=now)
        if agent['trusted']:
            update_data['last_trusted_seen'] = now
        await self.data_svc.update('agent', 'paw', link[0]['paw'], data=update_data)
        return json.dumps(dict(status=True))

    async def perform_action(self, link: typing.Dict) -> int:
        """
        Perform a link in the context of an operation, respecting the 'run', 'paused' and 'run_one_step' operation
        states. Calling data_svc.save('link', link) directly will schedule the link for execution,
        ignoring the state of the operation.
        :param link:
        :return: the id of the created link
        """
        operation_svc = self.get_service('operation_svc')
        op_id = link['op_id']
        operation = (await self.data_svc.get('operation', dict(id=op_id)))[0]
        while operation['state'] != operation_svc.op_states['RUNNING']:
            if operation['state'] == operation_svc.op_states['RUN_ONE_LINK']:
                link_id = await self.data_svc.save('link', link)
                await self.data_svc.update('operation', 'id', op_id, dict(state=operation_svc.op_states['PAUSED']))
                return link_id
            else:
                await asyncio.sleep(30)
                operation = (await self.data_svc.get('operation', dict(id=op_id)))[0]
        link.pop('adversary_map_id')
        return await self.data_svc.save('link', link)

    @staticmethod
    async def capable_agent_abilities(ability_set, agent):
        """
        Trim a list of abilities down to those an agent can actually execute
        :param ability_set:
        :param agent:
        :return:
        """
        abilities = []
        preferred = next((e['executor'] for e in agent['executors'] if e['preferred']))
        executors = [e['executor'] for e in agent['executors']]
        for ai in set([pa['ability_id'] for pa in ability_set]):
            total_ability = [ab for ab in ability_set if (ab['ability_id'] == ai)
                             and (ab['platform'] == agent['platform']) and (ab['executor'] in executors)]
            if len(total_ability) > 0:
                val = next((ta for ta in total_ability if ta['executor'] == preferred), total_ability[0])
                abilities.append(val)
        return abilities

    """ PRIVATE """

    async def _gather_payload(self, ability_id):
        payload = await self.data_svc.get('payload', criteria=dict(ability=ability_id))
        return payload[0]['payload'] if payload else ''

    async def _update_agent_executor(self, agent_id, new_executors, previous_executors):
        """
        Update the agent's core executor
        :param agent_id: string with the agent_id for the agent calling back
        :param new_executors: list with incoming executors being reported by deployed agent
        :param previous_executors: list of dict with previous executors and their preferred status
        :return: None
        """
        old_executors = [d['executor'] for d in (sorted(previous_executors, key=lambda i: i['preferred'],
                                                        reverse=True))]
        for item in set(new_executors) - set(old_executors):
            await self.data_svc.save('executor', dict(agent_id=agent_id, executor=item, preferred=0))

        if old_executors[0] != new_executors[0]:
            await self.data_svc.update('executor', 'agent_id', agent_id, data=dict(preferred=0))
            await self.data_svc.save('executor', dict(agent_id=agent_id, executor=new_executors[0], preferred=1))

        for item in set(old_executors) - set(new_executors):
            await self.data_svc.delete('executor', dict(agent_id=agent_id, executor=item))
