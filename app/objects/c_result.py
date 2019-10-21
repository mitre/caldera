from app.database.core_dao import CoreDao


class Result:

    def __init__(self, link_id, output, parsed=None):
        self.dao = CoreDao()
        self._link_id = int(float(link_id))
        self._output = output
        self._parsed = parsed
        self._link = None

    @property
    def link_id(self):
        return self._link_id

    @property
    def output(self):
        return self._output

    @property
    def parsed(self):
        return self._parsed

    @property
    def link(self):
        return self._link

    @link_id.setter
    def link_id(self, value):
        self._link_id = value

    @output.setter
    def output(self, value):
        self._output = value

    @parsed.setter
    def parsed(self, value):
        self._parsed = value

    async def save(self):
        await self.dao.create('core_result', dict(link_id=self.link_id, output=self.output))

    async def update(self):
        await self.dao.update('core_result', key='link_id', value=self.link_id, data=dict(parsed=self.parsed))

    async def attach_link(self):
        link = await self.dao.get('core_chain', dict(id=self.link_id))
        link[0]['facts'] = await self.dao.get('core_fact', dict(link_id=link[0]['id']))
        self._link = link[0]
