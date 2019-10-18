from app.database.memory import Memory
from app.database.persist import Persist


class CoreDao:

    def __init__(self, database=None, memory=False):
        if memory:
            self.db = Memory()
        else:
            self.db = Persist(database)

    async def build(self, schema):
        await self.db.build(schema)

    async def get(self, table, criteria=None):
        return await self.db.get(table, criteria)

    async def create(self, table, data):
        return await self.db.create(table, data)

    async def delete(self, table, data):
        return await self.db.delete(table, data)

    async def update(self, table, key, value, data):
        await self.db.update(table, key, value, data)

    async def get_in(self, table, field, elements):
        return await self.db.get_in(table, field, elements)
