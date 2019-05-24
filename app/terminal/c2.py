import asyncio
import csv
from base64 import b64decode
from multiprocessing import Process

from termcolor import colored


class C2:

    def __init__(self, services):
        self.shell_prompt = 'caldera> '
        self.data_svc = services.get('data_svc')
        self.operation_svc = services.get('operation_svc')
        self.modes = dict(
            agent=dict(view=lambda: self.view_agent(),
                       pick=lambda i: self.pick_agent(i)),
            ability=dict(view=lambda: self.view_ability(),
                         pick=lambda i: self.pick_ability(i)),
            adversary=dict(view=lambda: self.view_adversary(),
                           pick=lambda i: self.pick_adversary(i)),
            operation=dict(view=lambda: self.view_operation(),
                           pick=lambda i: self.pick_operation(i),
                           run=lambda: self.run_operation(),
                           delete=lambda i: self.delete_operation(i),
                           pause=lambda i: self.pause_operation(i),
                           resume=lambda i: self.resume_operation(i),
                           cancel=lambda i: self.cancel_operation(i),
                           options=[
                                dict(name='name', required=1, default=None, doc='1-word name for operation'),
                                dict(name='group', required=1, default=1, doc='group ID'),
                                dict(name='adversary', required=1, default=1, doc='adversary ID'),
                                dict(name='jitter', required=0, default='2/5', doc='seconds each agent will check in'),
                                dict(name='cleanup', required=0, default=1, doc='run cleanup for each ability'),
                                dict(name='stealth', required=0, default=0, doc='obfuscate the ability commands'),
                                dict(name='seed', required=0, default=None, doc='absolute path to a facts csv')
                           ])
        )

    def execute_mode(self, mode, cmd):
        try:
            chosen = self.modes.get(mode)
            if cmd == 'back':
                self.shell_prompt = 'caldera> '
            elif cmd == 'options':
                for option in chosen['options']:
                    print('--> %s = %s ... %s' % (option['name'], option['default'], option['doc']))
            elif cmd.startswith('set'):
                pieces = cmd.split(' ')
                option = next((o for o in chosen['options'] if o['name'] == pieces[1]), False)
                option['default'] = pieces[2]
            elif cmd == 'unset':
                for option in chosen['options']:
                    option['default'] = None
            elif cmd == 'missing':
                for option in chosen['options']:
                    if option['default'] is None and option['required']:
                        print('--> %s = %s' % (option['name'], option['default']))
            elif len(cmd.split(' ')) == 2:
                pieces = cmd.split(' ')
                self.modes[mode][pieces[0]](pieces[1])
            else:
                self.modes[mode][cmd]()
        except KeyError:
            print(colored('[-] Bad command', 'red'))
        except IndexError:
            print(colored('[-] No results found', 'red'))

    def view_agent(self):
        for a in asyncio.run(self.data_svc.explode_agents()):
            print('--> id:%s | host:%s | groups:%s' % (a['id'], a['hostname'], [g['id'] for g in a['groups']]))

    def pick_agent(self, i):
        for a in asyncio.run(self.data_svc.explode_agents(criteria=dict(id=i))):
            print('--> paw:%s | executor:%s | sleep:%s | checks:%s | last_seen:%s' %
                  (a['paw'], a['executor'], a['sleep'], a['checks'], a['last_seen']))

    def view_ability(self):
        for i, a in enumerate(asyncio.run(self.data_svc.explode_abilities())):
            print('--> id:%s | executor:%s | %s | %s' % (i, a['executor'], a['name'], a['description']))

    def pick_ability(self, i):
        abilities = asyncio.run(self.data_svc.explode_abilities())
        for a in asyncio.run(self.data_svc.explode_abilities(criteria=dict(id=abilities[int(i)]['id']))):
            print('--> technique:%s/%s' % (a['technique']['attack_id'], a['technique']['name']))
            print('--> executor:%s' % a['executor'])
            print('--> test:%s' % self._decode(a['test']))
            print('--> cleanup:%s' % self._decode(a['cleanup']))

    def view_adversary(self):
        for a in asyncio.run(self.data_svc.explode_adversaries()):
            print('--> id:%s | name:%s | description=%s' % (a['id'], a['name'], a['description']))

    def pick_adversary(self, i):
        for a in asyncio.run(self.data_svc.explode_adversaries(criteria=dict(id=i))):
            for phase, abilities in a['phases'].items():
                for ab in abilities:
                    print('phase:%s | executor:%s | %s' % (phase, ab['executor'], self._decode(ab['test'])))

    def view_operation(self):
        for a in asyncio.run(self.data_svc.explode_operation()):
            state = asyncio.run(self.operation_svc.get_state(a['id']))
            message = '--> id:%s | name:%s | group:%s | adversary:%s | start:%s | finish:%s' % (
                a['id'], a['name'], a['host_group']['id'], a['adversary']['id'], a['start'], a['finish'])
            if a['finish'] is None:
                message = message + ' | state:%s' % state
            print(message)

    def pick_operation(self, i):
        for a in asyncio.run(self.data_svc.explode_operation(criteria=dict(id=i))):
            for link in a['chain']:
                print('score:%s | status:%s | collect:%s | %s' % (link['score'], link['status'],
                      link['collect'], self._decode(link['command'])))

    def run_operation(self):
        operation = {o['name']: o['default'] for o in self.modes['operation']['options']}
        seed_file = operation.pop('seed')
        op_id = asyncio.run(self.data_svc.create_operation(**operation))
        if seed_file:
            with open(seed_file, 'r') as f:
                next(f)
                reader = csv.reader(f, delimiter=',')
                for line in reader:
                    fact = dict(op_id=op_id, fact=line[0], value=line[1], score=line[2], link_id=0, action=line[3])
                    asyncio.run(self.data_svc.dao.create('dark_fact', fact))
                    print(str(colored('[*] Pre-seeding %s' % line[0], 'green')))
        Process(target=lambda: asyncio.run(self.operation_svc.run(op_id))).start()
        print(colored('[*] Operation %s started' % op_id, 'green'))

    def cancel_operation(self, target):
        asyncio.run(self.operation_svc.cancel_operation(target))

    def pause_operation(self, target):
        asyncio.run(self.operation_svc.pause_operation(target))

    def resume_operation(self, target):
        asyncio.run(self.operation_svc.run_operation(target))

    def delete_operation(self, target):
        asyncio.run(self.data_svc.delete_operations(dict(id=target)))

    @staticmethod
    def _decode(blob):
        return b64decode(blob).decode('utf-8')
