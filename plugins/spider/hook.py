from plugins.spider.app.spider_svc import SpiderService

name = 'Spider'
description = 'Use the spider to Navigate CALDERA'
address = '/plugin/spider/gui'


async def enable(services):
    app = services.get('app_svc').application
    spider_svc = SpiderService(services)
    app.router.add_static('/spider', 'plugins/spider/static/', append_version=True)
    app.router.add_route('GET', '/plugin/spider/gui', spider_svc.splash)
