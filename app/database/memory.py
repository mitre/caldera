import sqlite3

from app.database.database import Database


class Memory(Database):

    def __init__(self):
        self.connection = sqlite3.connect(':memory:')
        super().__init__()

    async def build(self, schema):
        await self.build_schema(self.connection, schema)

    async def get(self, table, criteria=None):
        return await self.read(self.connection, table, criteria)

    async def create(self, table, data):
        return await self.add(self.connection, table, data)

    async def update(self, table, key, value, data):
        await self.upsert(self.connection, table, key, value, data)

    async def get_in(self, table, field, elements):
        return await self.read_in(self.connection, table,field, elements)

    async def delete(self, table, data):
        return await self.remove(self.connection, table, data)
