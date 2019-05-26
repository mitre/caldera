from app.terminal.mode import Mode


class Ability(Mode):

    def __init__(self, services, logger):
        super().__init__(services, logger)

    async def info(self):
        print('ABILITY allows you to view all ATT&CK technique implementations')
        print('-> search: list all abilities')
        print('-> pick: show the command and cleanup for a specified ability ID')

    async def execute(self, cmd):
        await self.execute_mode(cmd)

    async def search(self):
        abilities = []
        for i, a in enumerate(await self.data_svc.explode_abilities()):
            abilities.append(dict(id=i, technique=a['technique']['attack_id'], executor=a['executor'],
                                  name=a['name'], description=a['description']))
        self.log.console_table(abilities)

    async def pick(self, i):
        abilities = await self.data_svc.explode_abilities()
        for a in await self.data_svc.explode_abilities(criteria=dict(id=abilities[int(i)]['id'])):
            self.log.console_table([dict(executor=a['executor'],
                                         test=self.utility_svc.decode_bytes(a['test']),
                                         cleanup=self.utility_svc.decode_bytes(a['cleanup']))])
