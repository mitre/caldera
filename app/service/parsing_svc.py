from base64 import b64decode

import app.parsers.mimikatz as mimikatz_parser
import app.parsers.standard as parsers
from app.service.base_service import BaseService


class ParsingService(BaseService):

    def __init__(self):
        self.log = self.add_service('parsing_svc', self)
        self.parsers = {
            'json': parsers.json,
            'line': parsers.line,
            'mimikatz': mimikatz_parser.mimikatz
        }
        self.data_svc = self.get_service('data_svc')

    async def parse_facts(self, operation):
        """
        For a given operation, parse all facts for un-parsed results that have been sent in to the agent_svc
        :param operation:
        :return: None
        """
        results = await self.data_svc.explode_results()
        for result in [r for r in results if not r['parsed']]:
            parse_info = await self.data_svc.get('core_parser', dict(ability=result['link']['ability']))
            if parse_info and result['link']['status'] == 0:
                blob = b64decode(result['output']).decode('utf-8')
                parser = self.parsers.get(parse_info[0]['name'], parsers.regex)
                matched_facts = parser(parser=parse_info[0], blob=blob, log=self.log)

                await self._matched_fact_creation(matched_facts, operation, result)
                update = dict(parsed=self.get_current_timestamp())
                await self.data_svc.update('core_result', key='link_id', value=result['link_id'], data=update)

    """ PRIVATE """
    
    async def _add_parser(self, p_id, name, parser):
        """
        Load the specified parser plugin
        :param p_id:  the id of the yaml file that defines the parser
        :param name:  the unique name of the parser
        :param parser:  an instance of the parser class 
        :return: None
        """        
        if name in self.parsers:
            self.log.warning('Duplicate parser name detected:  %s:%s' % (p_id, name))
        else:
            self.parsers[name] = parser           

    async def _matched_fact_creation(self, matched_facts, operation, result):
        fact_relationship = self.get_service('planning_svc').get_operation_relationships(operation,
                                                                ability_id=result['link']['ability'],
                                                                relationship_type='consequence')
        source = (await self.data_svc.explode_sources(dict(name=operation['name'])))[0]
        for match in matched_facts:
            operation = (await self.data_svc.explode_operation(dict(id=operation['id'])))[0]
            if match['fact'].startswith('host'):
                fact = await self._create_host_fact(operation, match, source, result)
            else:
                fact = await self._create_global_fact(operation, match, source, result)
            if fact:
                await self.data_svc.create_fact(**fact)
                if fact_relationship:
                    await self._create_fact_relationship(fact_relationship, fact, result['link']['id'], operation)

    async def _create_fact_relationship(self, relationship, fact, link_id, operation):
        for r in relationship:
            used_facts = ([c['facts_used'] for c in operation['chain'] if c['id'] == link_id])[0]
            for f in used_facts:
                r_fact = ([j for j in operation['facts'] if j['id'] == f['fact_id']])[0]
                if r_fact['property'] == r['property1']:
                    await self.data_svc.dao.create('core_fact_relationships', dict(value1=r_fact['value'],
                                                                              relationship=r['relationship'],
                                                                              value2=fact['value']))

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
