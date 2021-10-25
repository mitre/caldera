from celery import Celery
from datetime import datetime, timedelta
import sqlite3

from app.objects.c_agent import Agent
from app.objects.c_ability import Ability
from app.objects.secondclass.c_link import Link
from app.utility.base_world import BaseWorld
from app.utility.celery_config import database_path

celery_app = Celery('caldera', include=['app.utility.tasks'])
celery_app.config_from_object('app.utility.celery_config:settings', namespace='celery')


@celery_app.task
def generate_new_links(link_status, jitter, agent, abilities, config):
    agent = Agent.load(agent)
    abilities = [Ability.load(ability) for ability in abilities]
    agent_links = []
    if agent.trusted:
        # _generate_new_links
        for ability in agent.capabilities(abilities):
            executor = agent.get_preferred_executor(ability)
            if not executor:
                continue

            if executor.HOOKS and executor.language and executor.language in executor.HOOKS:
                executor.HOOKS[executor.language](ability, executor)
            if executor.command:
                link = Link.load(dict(command=BaseWorld.encode_string(executor.test_with_config(config)), paw=agent.paw, score=0,
                                      ability=ability, executor=executor, status=link_status,
                                      jitter=BaseWorld.jitter(jitter)))
                agent_links.append(link)
    return agent_links


@celery_app.task
def clean():
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cur = conn.cursor()
        # remove entries older than 2 minutes
        expiration_min = 2
        date_done_utc = (datetime.utcnow() - timedelta(minutes=expiration_min)).strftime('%Y-%m-%d %H:%M:%S.%f')
        sql_cmd = 'DELETE FROM celery_taskmeta where date_done < "%s";' % date_done_utc
        cur.execute(sql_cmd)
        timestamp = (datetime.now() - timedelta(minutes=expiration_min)).strftime('%Y-%m-%d %H:%M:%S.%f')
        sql_cmd = 'DELETE FROM kombu_message where timestamp < "%s";' % timestamp
        cur.execute(sql_cmd)
        conn.commit()
        conn.close()
        return 'Clean up success'
    except Exception as e:
        return e
