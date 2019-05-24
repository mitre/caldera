import logging

from tabulate import tabulate
from prettytable import PrettyTable
from termcolor import colored


class Logger:
    """
    Custom logger: all logs will be sent to the .logs directory
    """
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger(name)
        handler = logging.FileHandler('%s/%s' % ('.logs', name))
        formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.console_colors = dict(red=lambda msg: print(colored('[-] %s' % msg, 'red')),
                                   green=lambda msg: print(colored('[*] %s' % msg, 'green')),
                                   yellow=lambda msg: print(colored(msg, 'yellow')))

    def debug(self, msg):
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.setLevel(logging.INFO)
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.setLevel(logging.WARNING)
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.setLevel(logging.ERROR)
        self.logger.error(msg)

    def console(self, msg, color='green'):
        self.console_colors[color](msg)

    @staticmethod
    def console_table(data):
        headers = [str(colored(h, 'red')) for h in data[0].keys()]
        rows = [list(dictionary.values()) for dictionary in data]
        rows.insert(0, headers)
        table = tabulate(rows, headers='firstrow', tablefmt='orgtbl')
        print(table, flush=True)

