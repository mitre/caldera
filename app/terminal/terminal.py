import asyncio
import csv
from base64 import b64decode
import textwrap

import aiomonitor
from tabulate import tabulate
from termcolor import colored


class TerminalApp(aiomonitor.Monitor):

    def do_help(self):
        self._sout.write('\n'+'Application commands:' + '\n')
        self._sout.write('\t'+'ab: view abilities (optional) ability ID' + '\n')
        self._sout.write('\t'+'ad: view adversaries (optional) adversary ID' + '\n')
        self._sout.write('\t'+'ag: view all running agents' + '\n')
        self._sout.write('\t'+'gr: view groups (optional) group ID' + '\n')
        self._sout.write('\t'+'op: view started operations (optional) operation ID to see the decision chain' + '\n')
        self._sout.write('\t'+'qu: queue an operation to be started later (required) operation name, adversary ID and group ID (optional) jitter fraction' + '\n')
        self._sout.write('\t'+'re: view a specific result (required) link ID - from the decision chain.' + '\n')
        self._sout.write('\t'+'st: start an operation. (required) a queued operation ID.' + '\n')
		self._sout.write('\t'+'bl: Import blacklist of facts via a csv file with columns [fact, value, score]. Command usage: bl [csv file path] [op_id]' + '\n')
        self._sout.write('\n'+'Generic commands:' + '\n')
        self._sout.write('\t'+'help: see this output again' + '\n')
        self._sout.write('\t'+'console: open an aysnc Python console' + '\n')
        self._sout.write('\t'+'ps: show task table' + '\n')

    def do_ag(self):
        service = self._locals['services']['data_svc']
        co = asyncio.run_coroutine_threadsafe(service.explode_agents(), loop=self._loop)
        agents = co.result()
        headers = ['id', 'hostname', 'paw', 'checks', 'last_seen', 'sleep', 'executor', 'server']
        self._output(headers, [list(x.values()) for x in agents])

    def do_gr(self, identifier=None):
        service = self._locals['services']['data_svc']
        co = asyncio.run_coroutine_threadsafe(service.explode_groups(dict(id=identifier)), loop=self._loop)
        groups = co.result()
        if identifier:
            self._output(['group_id', 'agent_id'], [[a['group_id'], a['agent_id']] for g in groups for a in g['agents']])
            return
        self._output(['id', 'name'], [[g['id'], g['name']] for g in groups])

    def do_ab(self, identifier=None):
        service = self._locals['services']['data_svc']
        co = asyncio.run_coroutine_threadsafe(service.explode_abilities(dict(id=identifier)), loop=self._loop)
        abilities = co.result()
        if identifier:
            command = self._decode(abilities[0]['test'])
            self._output(['command'], [[command]])
            return
        headers = ['id', 'tactic', 'name', 'description']
        abilities = sorted(abilities, key=lambda i: i['technique']['tactic'])
        rows = [[a['id'], a['technique']['tactic'], a['name'], a['description']] for a in abilities]
        self._output(headers, rows)

    def do_ad(self, identifier=None):
        service = self._locals['services']['data_svc']
        co = asyncio.run_coroutine_threadsafe(service.explode_adversaries(dict(id=identifier)), loop=self._loop)
        adversaries = co.result()
        if identifier:
            rows = []
            for adv in adversaries:
                for phase, abilities in adv['phases'].items():
                    for a in abilities:
                        rows.append([phase, a['id'], a['technique']['tactic'], a['name'], self._decode(a['test'])])
            self._output(['phase', 'ability_id', 'tactic', 'name', 'command'], rows)
            return
        rows = [[adv['id'], adv['name'], adv['description']] for adv in adversaries]
        self._output(['id', 'name', 'description'], rows)

    def do_op(self, identifier=None):
        service = self._locals['services']['data_svc']
        co = asyncio.run_coroutine_threadsafe(service.explode_operation(dict(id=identifier)), loop=self._loop)
        operations = co.result()
        if identifier:
            rows = [[l['id'], l['host_id'], l['status'], l['score'], l['collect'], self._decode(l['command'])] for l in operations[0]['chain']]
            self._output(['link_id', 'agent', 'status', 'score', 'executed', 'command'], rows)
            return
        rows = []
        for o in operations:
            group = o['host_group']['id']
            adversary = o['adversary']['id']
            rows.append([o['id'], o['name'], group, adversary, o['start'], o['finish'], o['phase']])
        self._output(['id', 'name', 'group', 'adversary', 'start', 'finish', 'completed phase'], rows)

    def do_qu(self, name, adversary_name, group_name, jitter='3/5'):
        service = self._locals['services']['data_svc']
        op = dict(name=name, group=group_name, adversary=adversary_name, jitter=jitter)
        co = asyncio.run_coroutine_threadsafe(service.create_operation(**op), loop=self._loop)
        self._sout.write(str(colored('\nQueued operation #%s. Start it with "st %s"' % (co.result(), co.result()), 'yellow')) + '\n')

    def do_re(self, link_id):
        service = self._locals['services']['data_svc']
        co = asyncio.run_coroutine_threadsafe(service.explode_results(dict(link_id=link_id)), loop=self._loop)
        for r in co.result():
            self._flush(self._decode(r['output']))

    def do_st(self, op_id):
        service = self._locals['services']['operation_svc']
        asyncio.run_coroutine_threadsafe(service.run(op_id), loop=self._loop)
        self._sout.write(str(colored('Started!', 'yellow')) + '\n')
	
	def add_facts_from_csv(self, csv_path, table_name, op_id):
		service = self._locals['services']['data_svc']
		with open(csv_path, 'r') as f:
		next(f)
		reader = csv.reader(f, delimiter=',')
		for line in reader:
			fact = dict(op_id=op_id, fact=line[0], value=line[1], score=line[2], link_id=0)
			asyncio.run_coroutine_threadsafe(service.dao.create(table_name, fact), loop=self._loop)
			self._sout.write(str(colored('Added %s to op #%s' % (line[0], op_id), 'yellow')) + '\n')

	def do_up(self, csv_path, op_id):
		self.add_facts_from_csv(csv_path, 'dark_fact', op_id)

	def do_bl(self, csv_path, op_id):
		self.add_facts_from_csv(csv_path,'dark_black_list',op_id)


    """ PRIVATE """

    @staticmethod
    def _decode(blob):
        return b64decode(blob).decode('utf-8')

    def _output(self, headers, rows):
        headers = [str(colored(h, 'red')) for h in headers]
        rows.insert(0, headers)
        rows = self._adjust_width(rows)
        table = tabulate(rows, headers='firstrow', tablefmt='orgtbl')
        self._sout.write(str(table) + '\n')

    def _flush(self, content):
        content = colored(content, 'yellow')
        self._sout.write(str(content) + '\n')

    @staticmethod
    def _adjust_width(rows):
        for row in rows:
            for n, el in enumerate(row):
                if isinstance(el, str):
                    row[n] = '\n'.join(textwrap.wrap(el, 75))
        return rows
