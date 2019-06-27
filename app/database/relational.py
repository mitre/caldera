import sqlite3


class Sql:

    def __init__(self, database):
        self.database = database

    async def build(self, schema):
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                cursor.executescript(schema)
                conn.commit()
        except Exception:
            pass

    async def get(self, table, criteria=None):
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
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

    async def unique(self, column, table):
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT distinct %s FROM %s' % (column, table))
            rows = cursor.fetchall()
            return [dict(ix) for ix in rows]

    async def create(self, table, data):
        with sqlite3.connect(self.database) as conn:
            try:
                cursor = conn.cursor()
                columns = ', '.join(data.keys())
                placeholders = ', '.join('?' * len(data))
                sql = 'INSERT INTO {} ({}) VALUES ({})'.format(table, columns, placeholders)
                cursor.execute(sql, tuple(data.values()))
                last_id = cursor.lastrowid
                conn.commit()
                return last_id
            except sqlite3.IntegrityError:
                try:
                    existing = await self.get(table, data)
                    return existing[0].get('id') if existing else None
                except Exception:
                    return None

    async def update(self, table, key, value, data):
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            for k, v in data.items():
                sql = 'UPDATE {} SET {} = (?) WHERE {} = "{}"'.format(table, k, key, value)
                cursor.execute(sql, (v,))
            conn.commit()

    async def get_in(self, table, field, elements):
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            sql = 'SELECT * FROM %s WHERE %s IN (%s)' % (table, field, ','.join(map(str, elements)))
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [dict(ix) for ix in rows]

    async def delete(self, table, data):
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            sql = 'DELETE FROM %s ' % table
            where = next(iter(data))
            value = data.pop(where)
            sql += (' WHERE %s = "%s"' % (where, value))
            for k, v in data.items():
                sql += (' AND %s = "%s"' % (k, v))
            cursor.execute(sql)
            conn.commit()

    async def raw_select(self, sql):
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [dict(ix) for ix in rows]

    async def raw_update(self, sql):
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
