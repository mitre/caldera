from app.utility.base_world import BaseWorld


class BaseObfuscator(BaseWorld):

    def run(self, link, **kwargs):
        agent = self.__getattribute__('agent')
        supported_platforms = self.__getattribute__('supported_platforms')
        if agent.platform in supported_platforms and link.ability.executor in agent.executors:
            o = self.__getattribute__(link.ability.executor)
            return o(link, **kwargs)
