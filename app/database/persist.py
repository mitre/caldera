import sqlite3

from app.database.database import Database


class Persist(Database):

    def __init__(self, database):
        self.database = database
        super().__init__()

    async def build(self, schema):
        with sqlite3.connect(self.database) as conn:
            await self.build_schema(conn, schema)

    async def get(self, table, criteria=None):
        with sqlite3.connect(self.database) as conn:
            return await self.read(conn, table, criteria)

    async def create(self, table, data):
        with sqlite3.connect(self.database) as conn:
            return await self.add(conn, table, data)

    async def update(self, table, key, value, data):
        with sqlite3.connect(self.database) as conn:
            await self.upsert(conn, table, key, value, data)

    async def get_in(self, table, field, elements):
        with sqlite3.connect(self.database) as conn:
            return await self.read_in(conn, table, field, elements)

    async def delete(self, table, data):
        with sqlite3.connect(self.database) as conn:
            return await self.remove(conn, table, data)
