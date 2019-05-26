from app.terminal.mode import Mode


class Adversary(Mode):

    def __init__(self, services, logger):
        super().__init__(services, logger)

    async def info(self):
        print('ADVERSARY mode allows you to view and build adversary profiles')

    async def search(self):
        adversaries = await self.data_svc.explode_adversaries()
        for adv in adversaries:
            adv.pop('phases')
        self.log.console_table(adversaries)

    async def use(self, i):
        data = [dict(phase=phase, executor=ab['executor'], test=self.utility_svc.decode_bytes(ab['test']))
                for a in await self.data_svc.explode_adversaries(criteria=dict(id=i))
                for phase, abilities in a['phases'].items()
                for ab in abilities]
        self.log.console_table(data)

    async def execute(self, cmd):
        await self.execute_mode(cmd)
