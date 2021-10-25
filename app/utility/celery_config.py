import os
import sqlite3
import yaml

path = os.getcwd() + '/conf/celery.yml'
with open(path, encoding='utf-8') as seed:
    config = yaml.safe_load(seed)

broker = config['celery_broker_url']
backend = config['celery_result_backend']

database_path = ''

if config['celery_db']:
    database_path = os.getcwd() + '/data/' + config['celery_db']
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    cur.execute('PRAGMA auto_vacuum = 1')
    if conn:
        conn.close()
    broker = broker + database_path
    backend = backend + database_path


settings = {'celery_result_backend': backend,
            'celery_broker_url': broker,
            'celery_beat_schedule': {
                'clean-db-every-30s': {
                    'task': 'app.utility.tasks.clean',
                    'schedule': 30.0
                }
            }
            }
