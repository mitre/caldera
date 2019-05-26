from app.terminal.mode import Mode


class Agent(Mode):

    def __init__(self, services, logger):
        super().__init__(services, logger)

    async def info(self):
        print('AGENT mode allows you to view all hosts running 54ndc47 agents')

    async def search(self):
        self.log.console_table(await self.data_svc.explode_agents())

    async def use(self, i):
        self.log.console_table(await self.data_svc.explode_agents(criteria=dict(id=i)))

    async def execute(self, cmd):
        await self.execute_mode(cmd)
