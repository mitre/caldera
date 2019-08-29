from app.service.base_service import BaseService


class PluginService(BaseService):

    def __init__(self, plugins):
        self.plugins = plugins
        self.log = self.add_service('plugin_svc', self)

    def get_plugins(self):
        """
        Get a list of all plugins
        :return: a list of plugins
        """
        return self.plugins
