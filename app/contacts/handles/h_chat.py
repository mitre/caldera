class Handle:

    def __init__(self, tag):
        self.tag = tag

    @staticmethod
    async def run(socket, path, services):
        message = await socket.recv()
        print(message)
        await socket.send(message)
