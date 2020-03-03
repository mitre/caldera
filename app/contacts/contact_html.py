from aiohttp_jinja2 import template

from app.utility.base_world import BaseWorld


class Html(BaseWorld):

    def __init__(self, services):
        self.name = 'html'
        self.description = 'Accept beacons through an HTML page'
        self.app_svc = services.get('app_svc')
        self.contact_svc = services.get('contact_svc')

    async def start(self):
        self.app_svc.application.router.add_route('GET', self.get_config('app.contact.html'), self._accept_beacon)

    """ PRIVATE """

    @template('html.html')
    async def _accept_beacon(self, request):
        dict(instructions=[])
