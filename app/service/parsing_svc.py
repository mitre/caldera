import plugins.stockpile.parsers.standard as parsers
import plugins.stockpile.parsers.mimikatz as mimikatz_parser
from base64 import b64decode

from app.service.base_service import BaseService


class ParsingService(BaseService):

    def __init__(self):
        self.log = self.add_service('parsing_svc', self)

    async def parse_facts(self, operation):
        data_svc = self.get_service('data_svc')
        results = await data_svc.explode_results()
        for result in [r for r in results if not r['parsed']]:
            parser = await data_svc.explode_parsers(dict(ability=result['link']['ability']))
            if parser and result['link']['status'] == 0:
                if parser[0]['name'] == 'json':
                    matched_facts = parsers.json(parser[0], b64decode(result['output']).decode('utf-8'), self.log)
                elif parser[0]['name'] == 'line':
                    matched_facts = parsers.line(parser[0], b64decode(result['output']).decode('utf-8'), self.log)
                elif parser[0]['name'] == 'mimikatz':
                    matched_facts = mimikatz_parser.mimikatz(b64decode(result['output']).decode('utf-8'), self.log)
                else:
                    matched_facts = parsers.regex(parser[0], b64decode(result['output']).decode('utf-8'), self.log)

                source = (await data_svc.explode_sources(dict(name=operation['name'])))[0]
                for match in matched_facts:
<<<<<<< HEAD
                    operation = (await data_svc.explode_operation(dict(id=operation['id'])))[0]
                    if match['fact'].startswith('host'):
                        fact = await self._create_host_fact(operation, match, source, result)
                    else:
                        fact = await self._create_global_fact(operation, match, source, result)
                    if fact:
                        await data_svc.create_fact(**fact)

=======
                    update_op = await data_svc.explode_operation(dict(id=operation['id']))
                    if 'private' in match['fact']:
                        facts_to_check = [f for f in update_op[0]['facts'] if f['property'] == match['fact'] 
                                        and f['value'] == match['value'] and f['score'] > 0]
                        agents_to_check = []
                        for f in facts_to_check:
                            link = await data_svc.explode_chain(criteria=dict(id=f['link_id']))
                            agents_to_check.append(link[0]['paw'])
                        if x['link']['paw'] not in agents_to_check:
                            await data_svc.create_fact(
                                source_id=op_source[0]['id'], link_id=x['link_id'], property=match['fact'],
                                value=match['value'], set_id=match['set_id'], score=1
                            )
                    else:
                        if not any(f['property'] == match['fact'] and f['value'] == match['value'] and f['score'] <= 0 for f in
                                update_op[0]['facts']):
                            await data_svc.create_fact(
                                source_id=op_source[0]['id'], link_id=x['link_id'], property=match['fact'],
                                value=match['value'], set_id=match['set_id'], score=1
                            )

                # mark result as parsed
>>>>>>> cc404eaa47287172965bced8dd11380318323cda
                update = dict(parsed=self.get_current_timestamp())
                await data_svc.update('core_result', key='link_id', value=result['link_id'], data=update)

    """ PRIVATE """

    @staticmethod
    async def _create_host_fact(operation, match, source, result):
        already_stashed = [f for f in operation['facts'] if f['property'] == match['fact'] and f['value'] == match['value'] and f['score'] > 0]
        agents_to_check = []
        for fact in already_stashed:
            link = next((lnk for lnk in operation['chain'] if lnk['id'] == fact['link_id']), False)
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
