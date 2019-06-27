from app.database.relational import Sql


class CoreDao:

    def __init__(self, database):
        self.db = Sql(database)

    async def build(self, schema):
        await self.db.build(schema)

    async def get(self, table, criteria=None):
        return await self.db.get(table, criteria)

    async def unique(self, column, table):
        return await self.db.unique(column, table)

    async def create(self, table, data):
        return await self.db.create(table, data)

    async def delete(self, table, data):
        return await self.db.delete(table, data)

    async def update(self, table, key, value, data):
        await self.db.update(table, key, value, data)

    async def get_in(self, table, field, elements):
        return await self.db.get_in(table, field, elements)

    async def raw_select(self, sql):
        return await self.db.raw_select(sql)

    async def raw_update(self, sql):
        return await self.db.raw_update(sql)


