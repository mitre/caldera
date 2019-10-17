from base64 import b64decode
from importlib import import_module

from app.service.base_service import BaseService


class ParsingService(BaseService):

    def __init__(self):
        self.log = self.add_service('parsing_svc', self)

    async def parse_facts(self, operation):
        """
        For a given operation, parse all facts for un-parsed results
        :param operation:
        :return: None
        """
        data_svc = self.get_service('data_svc')
        results = await data_svc.explode_results()
        for result in [r for r in results if not r['parsed']]:
            for parser_info in await data_svc.explode_parser(dict(ability=result['link']['ability'])):
                if result['link']['status'] != 0:
                    continue
                blob = b64decode(result['output']).decode('utf-8')
                parser_info['used_facts'] = await data_svc.explode_used(dict(link_id=result['link_id']))
                parser = await self._load_parser(parser_info)
                relationships = parser.parse(blob=blob)

                await self._matched_fact_creation(relationships, operation, data_svc, result)
                update = dict(parsed=self.get_current_timestamp())
                await data_svc.update('core_result', key='link_id', value=result['link_id'], data=update)

    """ PRIVATE """

    @staticmethod
    async def _load_parser(parser_info):
        parsing_module = import_module(parser_info['module'])
        return getattr(parsing_module, 'Parser')(parser_info)

    async def _matched_fact_creation(self, relationships, operation, data_svc, result):
        source = (await data_svc.explode_sources(dict(name=operation['name'])))[0]
        for relationship in relationships:
            operation = (await data_svc.explode_operation(dict(id=operation['id'])))[0]
            s = relationship.get_source()
            if s[0].startswith('host'):
                fact = await self._create_host_fact(operation, s, source, result)
            else:
                fact = await self._create_global_fact(operation, s, source, result)
            if fact:
                await data_svc.create_fact(**fact)

    @staticmethod
    async def _create_host_fact(operation, match, source, result):
        already_stashed = [f for f in operation['facts'] if f['property'] == match[0] and f['value'] == match[1] and f['score'] > 0]
        agents_to_check = []
        for fact in already_stashed:
            link = next((lnk for lnk in operation['chain'] if lnk['id'] == fact['link_id']), False)
            if link:
                agents_to_check.append(link['paw'])
        if result['link']['paw'] not in agents_to_check:
            return dict(source_id=source['id'], link_id=result['link_id'], property=match[0], value=match[1], score=1)

    @staticmethod
    async def _create_global_fact(operation, match, source, result):
        if not any(f['property'] == match[0] and f['value'] == match[1] and f['score'] <= 0 for f in
                   operation['facts']):
            return dict(source_id=source['id'], link_id=result['link_id'], property=match[0], value=match[1], score=1)
