import socket


class Handle:

    def __init__(self, tag):
        self.tag = tag

    @staticmethod
    async def run(message, services, caller):
        callback = message.pop('callback', None)
        message['executors'] = [e for e in message.get('executors', '').split(',') if e]
        message['contact'] = 'udp'
        await services.get('contact_svc').handle_heartbeat(**message)

        if callback:
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            sock.sendto('roger'.encode(), (caller, int(callback)))
