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
    async def pick(cls, i):
        pass

    @classmethod
    async def run(cls):
        pass

    async def execute_mode(self, cmd):
        try:
            if cmd == 'info':
                await self.info()
            elif cmd.startswith('search'):
                await self.search()
            elif 'pick' in cmd:
                pieces = cmd.split(' ')
                await self.pick(pieces[1])
            elif cmd == 'show options':
                self.log.console_table(self.options)
            elif cmd == 'show missing':
                missing = [opt for opt in self.options if opt['value'] is None and opt['required']]
                self.log.console_table(missing)
            elif cmd == 'unset':
                for opt in self.options:
                    opt['value'] = None
            elif cmd.startswith('set'):
                pieces = cmd.split(' ')
                option = next((opt for opt in self.options if opt['name'] == pieces[1]), False)
                option['value'] = pieces[2]
            elif cmd == 'run':
                await self.run()
            elif cmd == '':
                pass
            else:
                self.log.console('Bad command - are you in the right mode?', 'red')
        except IndexError:
            self.log.console('No results found', 'red')
        except Exception:
            self.log.console('Command not available', 'red')
