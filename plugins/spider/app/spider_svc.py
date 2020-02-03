from aiohttp_jinja2 import template


class SpiderService:

    def __init__(self, services):
        self.services = services
        self.auth_svc = self.services.get('auth_svc')
        self.data_svc = self.services.get('data_svc')
        self.rest_svc = self.services.get('rest_svc')

    @template('spider.html')
    async def splash(self, request):
        await self.auth_svc.check_permissions(request)
        adversaries = [a.display for a in await self.data_svc.locate('adversaries')]
        return dict(adversaries=sorted(adversaries, key=lambda a: a['name']))
