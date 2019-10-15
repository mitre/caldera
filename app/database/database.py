import sqlite3


class Database:

    @staticmethod
    async def build_schema(connection, schema):
        try:
            cursor = connection.cursor()
            cursor.executescript(schema)
            connection.commit()
        except Exception:
            pass

    @staticmethod
    async def read(connection, table, criteria=None):
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        sql = 'SELECT * FROM %s ' % table
        if criteria:
            where = next(iter(criteria))
            value = criteria.pop(where)
            if value:
                sql += (' WHERE %s = "%s"' % (where, value))
                for k, v in criteria.items():
                    sql += (' AND %s = "%s"' % (k, v))
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(ix) for ix in rows]

    async def add(self, connection, table, data):
        try:
            cursor = connection.cursor()
            columns = ', '.join(data.keys())
            placeholders = ', '.join('?' * len(data))
            sql = 'INSERT INTO {} ({}) VALUES ({})'.format(table, columns, placeholders)
            cursor.execute(sql, tuple(data.values()))
            last_id = cursor.lastrowid
            connection.commit()
            return last_id
        except sqlite3.IntegrityError:
            try:
                existing = await self.read(connection, table, data)
                return existing[0].get('id') if existing else None
            except Exception:
                return None

    @staticmethod
    async def upsert(connection, table, key, value, data):
        cursor = connection.cursor()
        for k, v in data.items():
            sql = 'UPDATE {} SET {} = (?) WHERE {} = "{}"'.format(table, k, key, value)
            cursor.execute(sql, (v,))
        connection.commit()

    @staticmethod
    async def read_in(connection, table, field, elements):
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        sql = 'SELECT * FROM {} WHERE {} IN ({})'.format(table, field, ','.join('?'*len(elements)))
        cursor.execute(sql, elements)
        rows = cursor.fetchall()
        return [dict(ix) for ix in rows]

    @staticmethod
    async def remove(connection, table, data):
        cursor = connection.cursor()
        sql = 'DELETE FROM %s ' % table
        where = next(iter(data))
        value = data.pop(where)
        sql += (' WHERE %s = "%s"' % (where, value))
        for k, v in data.items():
            sql += (' AND %s = "%s"' % (k, v))
        cursor.execute(sql)
        connection.commit()
