import ast
import asyncio
import traceback

from datetime import datetime
from importlib import import_module

from app.objects.c_agent import Agent
from app.utility.base_service import BaseService


class AppService(BaseService):

    def __init__(self, config, plugins):
        self.config = config
        self.plugins = plugins
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
                next_check = self.config['untrusted_timer']
                for a in trusted_agents:
                    last_trusted_seen = datetime.strptime(a.last_trusted_seen, '%Y-%m-%d %H:%M:%S')
                    silence_time = (datetime.now() - last_trusted_seen).total_seconds()
                    if silence_time > (self.config['untrusted_timer'] + a.sleep_max):
                        await self.get_service('data_svc').store(Agent(paw=a.paw, trusted=0))
                    else:
                        trust_time_left = self.config['untrusted_timer'] - silence_time
                        if trust_time_left < next_check:
                            next_check = trust_time_left
        except Exception as e:
            self.log.error('[!] start_sniffer_untrusted_agents: %s' % e)

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

    async def resume_operations(self):
        """
        Resume all unfinished operations
        :return: None
        """
        for op in await self.get_service('data_svc').locate('operations', match=dict(finish=None)):
            self.log.debug('Resuming operation: %s' % op.name)
            self.loop.create_task(self.run_operation(op))

    async def run_operation(self, operation):
        try:
            self.log.debug('Starting operation: %s' % operation.name)
            planner = await self._get_planning_module(operation)
            for phase in operation.adversary.phases:
                await planner.execute(phase)
                await operation.wait_for_phase_completion()
                operation.phase = phase
            await self._cleanup_operation(operation)
            await operation.close()
            self.log.debug('Completed operation: %s' % operation.name)
        except Exception:
            traceback.print_exc()

    def get_plugins(self):
        """
        Get a list of all plugins
        :return: a list of plugins
        """
        return self.plugins

    """ PRIVATE """

    async def _get_planning_module(self, operation):
        planning_module = import_module(operation.planner.module)
        planner_params = ast.literal_eval(operation.planner.params)
        return getattr(planning_module, 'LogicalPlanner')(operation, self.get_service('planning_svc'), **planner_params)

    async def _cleanup_operation(self, operation):
        for member in operation.agents:
            for link in await self.get_service('planning_svc').select_cleanup_links(operation, member):
                operation.add_link(link)
        await operation.wait_for_phase_completion()


