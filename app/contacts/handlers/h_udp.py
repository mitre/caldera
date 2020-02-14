import socket

from app.objects.secondclass.c_fact import Fact


class Handler:

    TAGS = dict(
        process=lambda m, s, c: process_handler(m, s, c),
        beacon=lambda m, s, c: beacon_handler(m, s, c)
    )

    def __init__(self, tag):
        self.func = self.TAGS[tag]

    async def handle(self, message, services, caller):
        await self.func(message, services, caller)


async def process_handler(message, services, caller):
    process = message['result']['name'].lower()
    op = (await services.get('data_svc').locate('operations'))[0]
    for fact in op.source.facts:
        if fact.trait == 'host.process.unauthorized' and fact.value == process:
            op.hanging_facts.append(Fact(trait='host.process.unauthorized', value=process['pid']))


async def beacon_handler(message, services, caller):
    callback = message.pop('callback', None)
    message['executors'] = [e for e in message.get('executors', '').split(',') if e]
    message['contact'] = 'udp'
    await services.get('contact_svc').handle_heartbeat(**message)

    if callback:
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        sock.sendto('roger'.encode(), (caller, int(callback)))
