import logging
import hashlib

from app.utility.base_world import BaseWorld


class BaseObfuscator(BaseWorld):

    def __init__(self, agent):
        self.agent = agent

    def run(self, link, **kwargs):
        agent = self.__getattribute__('agent')
        supported_platforms = self.__getattribute__('supported_platforms')
        try:
            if agent.platform in supported_platforms and link.ability.executor in agent.executors:
                link.command_hash = hashlib.sha256(str.encode(link.command)).hexdigest()
                o = self.__getattribute__(link.ability.executor)
                return o(link, **kwargs)
        except Exception:
            logging.error('Failed to run BaseObfuscator, returning default decoded bytes')

        return self.decode_bytes(link.command)
