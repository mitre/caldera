import os
import sqlite3
import yaml

path = 'conf/celery.yml'
with open(path, encoding='utf-8') as seed:
    config = yaml.load(seed, Loader=yaml.FullLoader)

broker = config['celery_broker_url']
backend = config['celery_result_backend']
if config['celery_db']:
    db_path = os.getcwd() + '/data/' + config['celery_db']
    conn = sqlite3.connect(db_path)
    if conn:
        conn.close()
    broker = broker + db_path
    backend = backend + db_path

settings = {'celery_result_backend': backend,
            'celery_broker_url': broker}
