import json

from datetime import datetime


class Handler:

    TAGS = dict(
        terminal=lambda s, p, svc: terminal_handler(s, p, svc)
    )

    def __init__(self, tag):
        self.func = self.TAGS[tag]

    async def handle(self, socket, path, services):
        await self.func(socket, path, services)


async def terminal_handler(socket, path, services):
    session_id = path.split('/')[2]
    cmd = await socket.recv()
    handler = services.get('term_svc').socket_conn.tcp_handler
    paw = next(i.paw for i in handler.sessions if i.id == int(session_id))
    services.get('term_svc').reverse_report[paw].append(
        dict(date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cmd=cmd)
    )
    status, pwd, reply = await handler.send(session_id, cmd)
    await socket.send(json.dumps(dict(response=reply.strip(), pwd=pwd)))
