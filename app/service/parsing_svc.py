import app.parsers.standard as parsers
import app.parsers.mimikatz as mimikatz_parser
from base64 import b64decode

from app.service.base_service import BaseService


class ParsingService(BaseService):

    def __init__(self):
        self.log = self.add_service('parsing_svc', self)
        self.parsers = {
            'json': parsers.json,
            'line': parsers.line,
            'mimikatz': mimikatz_parser.mimikatz,
            'testing': parsers.testing
        }

    async def parse_facts(self, operation):
        """
        For a given operation, parse all facts for un-parsed results that have been sent in to the agent_svc
        :param operation:
        :return: None
        """
        data_svc = self.get_service('data_svc')
        results = await data_svc.explode_results()
        for result in [r for r in results if not r['parsed']]:
            parse_info = await data_svc.explode_parsers(criteria=dict(ability=result['link']['ability']))
            if parse_info and result['link']['status'] == 0:
                blob = b64decode(result['output']).decode('utf-8')
                parser = self.parsers.get(parse_info[0]['name'], parsers.regex)
                matched_facts = parser(parser=parse_info[0], blob=blob, log=self.log)

                await self._matched_fact_creation(matched_facts, operation, data_svc, result)
                update = dict(parsed=self.get_current_timestamp())
                await data_svc.update('core_result', key='link_id', value=result['link_id'], data=update)

    """ PRIVATE """

    async def _matched_fact_creation(self, matched_facts, operation, data_svc, result):
        source = (await data_svc.explode_sources(dict(name=operation['name'])))[0]
        fact_relationship = await data_svc.dao.get('core_ability_relationships',
                                                            criteria=dict(ability_id=result['link']['ability'],
                                                            relationship_type='creates'))
        for i, match in enumerate(matched_facts):
            operation = (await data_svc.explode_operation(dict(id=operation['id'])))[0]
            if match['fact'].startswith('host'):
                fact = await self._create_host_fact(operation, match, source, result)
            else:
                fact = await self._create_global_fact(operation, match, source, result)
            if fact:
                await data_svc.create_fact(**fact)
            if fact_relationship and i < len(matched_facts)-1:
                fact_pair = await self._create_fact_relationship(match, matched_facts[i+1:], fact_relationship[0])
                if fact_pair:
                    await data_svc.create('core_fact_relationships', fact_pair)

    @staticmethod
    async def _create_host_fact(operation, match, source, result):
        already_stashed = [f for f in operation['facts'] if f['property'] == match['fact'] and f['value'] == match['value'] and f['score'] > 0]
        agents_to_check = []
        for fact in already_stashed:
            link = next((lnk for lnk in operation['chain'] if lnk['id'] == fact['link_id']), False)
            if link:
                agents_to_check.append(link['paw'])
        if result['link']['paw'] not in agents_to_check:
            return dict(source_id=source['id'], link_id=result['link_id'], property=match['fact'], value=match['value'],
                        set_id=match['set_id'], score=1)

    @staticmethod
    async def _create_global_fact(operation, match, source, result):
        if not any(f['property'] == match['fact'] and f['value'] == match['value'] and f['score'] <= 0 for f in
                   operation['facts']):
            return dict(source_id=source['id'], link_id=result['link_id'], property=match['fact'],
                        value=match['value'], set_id=match['set_id'], score=1)

    @staticmethod
    async def _create_fact_relationship(fact1, sliced_facts, fact_relationship):
        for fact2 in sliced_facts:
            if fact1['set_id'] == fact2['set_id']:
                return(dict(value1=fact1['value'], relationship=fact_relationship['relationship'],
                            value2=fact2['value']))