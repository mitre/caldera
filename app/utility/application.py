import asyncio

from datetime import datetime

from app.objects.c_agent import Agent
from app.utility.base_world import BaseWorld


class Application(BaseWorld):

    def __init__(self, services, config):
        self.services = services
        self.config = config
        self.log = self.create_logger('application')
        self.loop = asyncio.get_event_loop()

    async def start_sniffer_untrusted_agents(self):
        """
        Cyclic function that repeatedly checks if there are agents to be marked as untrusted
        :return: None
        """
        next_check = self.config['untrusted_timer']
        try:
            while True:
                await asyncio.sleep(next_check + 1)
                trusted_agents = await self.services.get('data_svc').locate('agents', match=dict(trusted=1))
                next_check = self.config['untrusted_timer']
                for a in trusted_agents:
                    last_trusted_seen = datetime.strptime(a.last_trusted_seen, '%Y-%m-%d %H:%M:%S')
                    silence_time = (datetime.now() - last_trusted_seen).total_seconds()
                    if silence_time > (self.config['untrusted_timer'] + a.sleep_max):
                        await self.services.get('data_svc').store(Agent(paw=a.paw, trusted=0))
                    else:
                        trust_time_left = self.config['untrusted_timer'] - silence_time
                        if trust_time_left < next_check:
                            next_check = trust_time_left
        except Exception as e:
            self.log.error('[!] start_sniffer_untrusted_agents: %s' % e)

    async def resume_operations(self):
        """
        Resume all unfinished operations
        :return: None
        """
        for op in await self.services.get('data_svc').locate('operations', match=dict(finish=None)):
            self.loop.create_task(op.run())
