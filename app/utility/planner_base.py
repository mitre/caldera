import asyncio


class PlannerBase:
    def __init__(self, data_svc, utility_svc, log):
        self.data_svc = data_svc
        self.utility_svc = utility_svc
        self.log = log
        self.loop = asyncio.get_event_loop()

    async def execute(self, operation, phase, controller):
        for member in operation['host_group']['agents']:
            agent = await self.data_svc.dao.get('core_agent', dict(id=member['agent_id']))
            return await self._exhaust_agent(agent[0], operation, phase, controller)

    async def _exhaust_agent(self, agent, operation, phase, controller):
        while True:
            operation = await self.wait_for_agent(operation['id'], agent['id'])
            cancel = await controller.check_status(operation['id'])
            if cancel == 'Cancel Requested':
                return cancel
            link, cleanup = await self.choose_next_link(operation, agent, phase)
            if not link:
                break
            await self.handle_links(link, cleanup)

    async def handle_links(self, link, cleanup):
        print("This function needs to be implemented/made available in your planner.")
        return None

    async def wait_for_agent(self, op_id, agent_id):
        print("This function needs to be implemented/made available in your planner.")
        return None

    async def choose_next_link(self, operation, agent, phase):
        print("This function needs to be implemented/made available in your planner.")
        return None, None