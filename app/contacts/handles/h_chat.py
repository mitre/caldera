import asyncio

class Handle:

    def __init__(self, tag):
        self.tag = tag

    @staticmethod
    async def run(socket, path, services, users):
        while True:
            message = await socket.recv()
            await asyncio.wait([ws.send(message) for ws in users])
