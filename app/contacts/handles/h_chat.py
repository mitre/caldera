class Handle:

    def __init__(self, tag):
        self.tag = tag

    @staticmethod
    async def run(socket, path, services):
        while True:
            message = await socket.recv()
            await socket.send(message)
