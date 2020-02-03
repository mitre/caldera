import re

from aiohttp import web
from aiohttp_jinja2 import template


class FactGraphAPI:

    def __init__(self, services):
        self.data_svc = services.get('data_svc')
        self.utility_svc = services.get('utility_svc')

    @template('factgraph.html')
    async def landing(self, request):
        pass

    async def rest_api(self, request):
        data = dict(await request.json())
        index = data.pop('index')
        options = dict(
            POST=dict(
                fact_graph=lambda d: self._build_graph_nodes_links()
            )
        )
        output = await options[request.method][index](data)
        return web.json_response(output)

    """ PRIVATE """

    async def _build_fact_preconditions(self, criteria=None):
        abilities = await self.data_svc.explode_abilities(criteria=criteria)
        for ab in abilities:
            decoded_fact = self.utility_svc.decode_bytes(ab['test'])
            ab['requires'] = list(set(re.findall('#{([^}]+)}', decoded_fact)))
        return abilities

    async def _build_graph_nodes_links(self):
        abilities = await self._build_fact_preconditions()
        nodes, facts, links = [], [], []
        for ab in abilities:
            fact_found = False
            for p in ab['parser']:
                if not any(p['property'] == f['id'] for f in facts):
                    facts.append(dict(id=p['property'], type='fact', label=p['property']))
                links.append(dict(source=ab['ability_id']+ab['platform'], target=p['property'], label='unlocks'))
                fact_found = True
            for r in ab['requires']:
                if not any(r == f['id'] for f in facts):
                    facts.append(dict(id=r, type='fact', label=r))
                links.append(dict(source=r, target=ab['ability_id']+ab['platform'], label='required'))
                fact_found = True
            if fact_found and not any(ab['ability_id']+ab['platform'] == n['id'] for n in nodes):
                nodes.append(dict(id=ab['ability_id']+ab['platform'], type='ability', label=ab['name'],
                                  platform=ab['platform']))
        return dict(nodes=nodes+facts, links=links)