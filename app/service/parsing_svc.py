import glob
from base64 import b64decode
from pydoc import locate

from app.service.base_service import BaseService


class ParsingService(BaseService):

    def __init__(self):
        self.parsers = dict()
        self.log = self.add_service('parsing_svc', self)
        
    async def load_parser(self, p_id, name, parser):
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
        
    async def load_parsers(self, directory):
        """
        Load all parser plugins
        :param directory:
        :return: None
        """
        for filename in glob.iglob('%s/*.yml' % directory, recursive=False):
            for entries in self.strip_yml(filename):
                parser = locate(entries['class'])
                if parser:
                    parser = parser(self.log)
                else:
                    self.log.warning('Unable to find parser class %s' % entries['class'])
                    next
                if isinstance(entries['name'], str):                    
                    await self.load_parser(entries['id'], entries['name'], parser)
                else:
                    for name in entries['name']:
                        await self.load_parser(entries['id'], name, parser)                    

    async def parse_facts(self, operation):
        """
        For a given operation, parse all facts for un-parsed results that have been sent in to the agent_svc
        :param operation:
        :return: None
        """
        data_svc = self.get_service('data_svc')
        results = await data_svc.explode_results()
        for result in [r for r in results if not r['parsed']]:
            parser = await data_svc.get('core_parser', dict(ability=result['link']['ability']))
            if parser and result['link']['status'] == 0:
                if parser[0]['name'] in self.parsers:
                    matched_facts = self.parsers[parser[0]['name']].parse(parser[0], b64decode(result['output']).decode('utf-8'))
                else:                
                    self.log.error('Unable to find parser %s' % parser[0]['name'])
                    matched_facts = []

                source = (await data_svc.explode_sources(dict(name=operation['name'])))[0]
                for match in matched_facts:
                    operation = (await data_svc.explode_operation(dict(id=operation['id'])))[0]
                    if match['fact'].startswith('host'):
                        fact = await self._create_host_fact(operation, match, source, result)
                    else:
                        fact = await self._create_global_fact(operation, match, source, result)
                    if fact:
                        await data_svc.create_fact(**fact)

                update = dict(parsed=self.get_current_timestamp())
                await data_svc.update('core_result', key='link_id', value=result['link_id'], data=update)

    """ PRIVATE """

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
