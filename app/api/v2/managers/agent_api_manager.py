from app.api.v2.managers.base_api_manager import BaseApiManager


class AgentApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def get_deploy_commands(self):
        deployment_ability_ids = tuple(self.get_config(name='agents', prop='deployments'))
        deployment_abilities = []
        for id in deployment_ability_ids:
            deployment_abilities.append((await self._data_svc.locate('abilities', {'ability_id': id}))[0])

        raw_abilities = []
        for ability in deployment_abilities:
            for executor in ability.executors:
                variations = [{'description': v.description, 'command': v.raw_command} for v in executor.variations]
                raw_abilities.append({'name': ability.name, 'platform': executor.platform, 'executor': executor.name,
                                      'description': ability.description, 'command': executor.command,
                                      'variations': variations})

        app_config = {k: v for k, v in self.get_config().items() if k.startswith('app.')}
        app_config.update({f'agents.{k}': v for k, v in self.get_config(name='agents').items()})

        return dict(abilities=raw_abilities, app_config=app_config)
