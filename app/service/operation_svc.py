import asyncio
import ast
import traceback

from importlib import import_module

from app.utility.base_service import BaseService


class OperationService(BaseService):

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.log = self.add_service('operation_svc', self)
        self.data_svc = self.get_service('data_svc')

    async def resume(self):
        """
        Resume an operation that was stopped
        :return: None
        """
        for op in await self.data_svc.locate('operations'):
            if not op.finish:
                self.loop.create_task(self.run(op.name))

    async def close_operation(self, operation):
        """
        Perform all close actions for an operation
        :param operation:
        :return: None
        """
        self.log.debug('Operation complete: %s' % operation.name)
        operation.state = operation.states['FINISHED']
        operation.finish = self.get_current_timestamp()

    async def run(self, name):
        """
        Run a new operation
        :param name:
        :return: None
        """
        self.log.debug('Starting operation: %s' % name)
        operation = await self.data_svc.locate('operations', dict(name=name))
        try:
            planner = await self._get_planning_module(operation[0])
            for phase in operation[0].adversary.phases:
                await planner.execute(phase)
                await self._wait_for_phase_completion(operation[0])
                operation[0].phase = phase
            await self._run_cleanup_actions(name)
            await self.close_operation(operation[0])
        except Exception:
            traceback.print_exc()

    """ PRIVATE """

    async def _get_planning_module(self, operation):
        planning_module = import_module(operation.planner.module)
        planner_params = ast.literal_eval(operation.planner.params)
        return getattr(planning_module, 'LogicalPlanner')(operation, self.get_service('planning_svc'), **planner_params)

    async def _wait_for_phase_completion(self, operation):
        for member in operation.agents:
            if (not member.trusted) and (not operation.allow_untrusted):
                continue
            while next((True for lnk in operation.chain if lnk.paw == member.paw and not lnk.finish and not lnk.status == self.LinkState.DISCARD.value),
                       False):
                await asyncio.sleep(3)
                if await self._trust_issues(operation, member.paw):
                    break

    async def _trust_issues(self, operation, paw):
        if not operation.allow_untrusted:
            agent = await self.data_svc.locate('agents', match=dict(paw=paw))
            return not agent[0].trusted
        return False

    async def _run_cleanup_actions(self, name):
        operation = (await self.data_svc.locate('operations', match=dict(name=name)))[0]
        for member in operation.agents:
            for link in await self.get_service('planning_svc').select_cleanup_links(operation, member):
                operation.add_link(link)
        await self._wait_for_phase_completion(operation)

