from base64 import b64decode

from app.service.base_service import BaseService


class ParsingService(BaseService):

    def __init__(self):
        self.log = self.add_service('parsing_svc', self)
        self.data_svc = self.get_service('data_svc')

    async def parse_facts(self, operation):
        """
        For a given operation, parse all facts for un-parsed results
        :param operation:
        :return: None
        """
        results = await self.data_svc.explode('result')
        for result in [r for r in results if not r['parsed']]:
            for parser_info in await self.data_svc.explode('parser', dict(ability=result['link']['ability'])):
                if result['link']['status'] != 0:
                    continue
                blob = b64decode(result['output']).decode('utf-8')
                parser_info['used_facts'] = await self.data_svc.explode('used', dict(link_id=result['link_id']))
                parser = await self.load_module('Parser', parser_info)
                relationships = parser.parse(blob=blob)

                await self._update_scores(link_id=result['link_id'], increment=len(relationships))
                await self._create_relationships(relationships, operation, result)

                update = dict(parsed=self.get_current_timestamp())
                await self.data_svc.update('result', key='link_id', value=result['link_id'], data=update)

    """ PRIVATE """

    async def _create_relationships(self, relationships, operation, result):
        source = (await self.data_svc.explode('source', dict(name=operation['name'])))[0]
        for relationship in relationships:
            operation = (await self.data_svc.explode('operation', dict(id=operation['id'])))[0]
            s_id = await self._save_fact_entry(operation, relationship.get_source(), source, result)
            t_id = await self._save_fact_entry(operation, relationship.get_target(), source, result)
            await self._save_relationship(result['link_id'], s_id, relationship.get_edge(), t_id)

    async def _save_fact_entry(self, operation, prop, source, result):
        if prop[0] and prop[0].startswith('host'):
            fact = await self._build_host_fact(operation, prop, source, result)
        else:
            fact = await self._build_global_fact(operation, prop, source, result)
        if fact and fact['property']:
            return await self.data_svc.save('fact', fact)
        return await self._get_fact_id(operation, prop)

    @staticmethod
    async def _get_fact_id(operation, prop):
        for fact in operation['facts']:
            if fact['property'] == prop[0] and fact['value'] == prop[1]:
                return fact['id']

    @staticmethod
    async def _build_host_fact(operation, match, source, result):
        already_stashed = [f for f in operation['facts'] if f['property'] == match[0] and f['value'] == match[1] and f['score'] > 0]
        agents_to_check = []
        for fact in already_stashed:
            link = next((lnk for lnk in operation['chain'] if lnk['id'] == fact['link_id']), False)
            if link:
                agents_to_check.append(link['paw'])
        if result['link']['paw'] not in agents_to_check:
            return dict(source_id=source['id'], link_id=result['link_id'], property=match[0], value=match[1], score=1)

    @staticmethod
    async def _build_global_fact(operation, match, source, result):
        if not any(f['property'] == match[0] and f['value'] == match[1] for f in operation['facts']):
            return dict(source_id=source['id'], link_id=result['link_id'], property=match[0], value=match[1], score=1)

    async def _save_relationship(self, link_id, source_id, edge, target_id):
        if source_id and edge:
            relationship = dict(link_id=link_id, source=source_id, edge=edge, target=target_id)
            await self.data_svc.save('relationship', relationship)

    async def _update_scores(self, link_id, increment):
        used_facts = await self.data_svc.get('used', dict(link_id=link_id))
        for uf in used_facts:
            existing = (await self.data_svc.get('fact', dict(id=uf['fact_id'])))[0]
            update = dict(score=existing['score'] + increment)
            await self.data_svc.update('fact', key='id', value=uf['fact_id'], data=update)
