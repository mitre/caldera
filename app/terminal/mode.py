from abc import ABC


class Mode(ABC):

    def __init__(self, services, logger):
        self.data_svc = services.get('data_svc')
        self.utility_svc = services.get('utility_svc')
        self.operation_svc = services.get('operation_svc')
        self.log = logger

    @classmethod
    async def info(cls):
        pass

    @classmethod
    async def search(cls):
        pass

    @classmethod
    async def use(cls, i):
        pass

    async def execute_mode(self, cmd):
        try:
            if cmd == 'info':
                await self.info()
            elif cmd == 'search':
                await self.search()
            elif 'use' in cmd:
                pieces = cmd.split(' ')
                await self.use(pieces[1])
            elif cmd == '':
                pass
            else:
                pass
        except IndexError:
            self.log.console('No results found', 'red')
        except Exception:
            self.log.console('Bad command', 'red')
