import logging


class Logger:
    """
    Custom logger. By default, all logs will be:
        1) logged to console
        2) To a file in the .logs directory
        3) (optionally) sent to a 3rd party like Logstash

    EXAMPLE: To direct logs to Logstash: replace the handler with:
        import logstash
        self.logger.addHandler(logstash.LogstashHandler(logstash_fqdn, 5959))
    """
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger(name)
        handler = logging.FileHandler('%s/%s' % ('.logs', name))
        formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

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
