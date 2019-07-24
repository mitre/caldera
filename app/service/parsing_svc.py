import plugins.stockpile.parsers.standard as parsers
import plugins.stockpile.parsers.mimikatz as mimikatz_parser
from base64 import b64decode
from datetime import datetime


class ParsingService:

    def __init__(self, data_svc):
        self.data_svc = data_svc

    async def parse_facts(self, operation):
        sql = 'SELECT b.id, b.ability, a.output, a.link_id FROM core_result a inner join core_chain b on a.link_id=b.id ' \
              'where b.op_id = %s and a.parsed is null;' % operation['id']
        op_source = await self.data_svc.dao.get('core_source', dict(name=operation['name']))
        for x in await self.data_svc.dao.raw_select(sql):
            parser = await self.data_svc.dao.get('core_parser', dict(ability=x['ability']))
            if parser:
                if parser[0]['name'] == 'json':
                    matched_facts = parsers.json(parser[0], b64decode(x['output']).decode('utf-8'))
                elif parser[0]['name'] == 'line':
                    matched_facts = parsers.line(parser[0], b64decode(x['output']).decode('utf-8'))
                elif parser[0]['name'] == 'mimikatz':
                    matched_facts = mimikatz_parser.mimikatz(b64decode(x['output']).decode('utf-8'))
                else:
                    matched_facts = parsers.regex(parser[0], b64decode(x['output']).decode('utf-8'))

                # save facts to DB
                for match in matched_facts:
                    if not any(f['property'] == match['fact'] and f['value'] == match['value'] and f['blacklist'] for f in
                               operation['facts']):
                        await self.data_svc.create_fact(
                            source_id=op_source[0]['id'], link_id=x['id'], property=match['fact'], value=match['value'],
                            set_id=match['set_id'], score=1, blacklist=0
                        )

                # mark result as parsed
                update = dict(parsed=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                await self.data_svc.dao.update('core_result', key='link_id', value=x['link_id'], data=update)

