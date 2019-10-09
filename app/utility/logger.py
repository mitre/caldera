import logging


class Logger:
    """
    Custom logger: all logs will be sent to the logs directory
    """
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger(name)

        project_root = Path(__file__).parents[2]
        handler = logging.FileHandler(Path().joinpath(project_root, 'logs/%s.log' % name))
        handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
        self.logger.addHandler(handler)

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)
