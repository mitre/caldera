import logging

from termcolor import colored


class Logger:
    """
    Custom logger: all logs will be sent to the .logs directory
    """
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger(name)
        handler = logging.FileHandler('%s/%s.log' % ('.logs', name))
        handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
        self.logger.addHandler(handler)
        self.console_colors = dict(red=lambda msg: print(colored('[-] %s' % msg, 'red')),
                                   green=lambda msg: print(colored('[+] %s' % msg, 'green')),
                                   blue=lambda msg: print(colored('[*] %s' % msg, 'blue')),
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
        headers = list(data[0].keys())
        header_list = [headers]
        for item in data:
            header_list.append([str(item[col] or '') for col in headers])
        column_size = [max(map(len, col)) for col in zip(*header_list)]
        row_format = ' | '.join(['{{:<{}}}'.format(i) for i in column_size])
        header_list.insert(1, ['-' * i for i in column_size])
        for item in header_list:
            print(row_format.format(*item))
