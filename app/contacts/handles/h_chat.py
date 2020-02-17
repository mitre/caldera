import websockets


class Handle:

    def __init__(self, tag):
        self.tag = tag

    @staticmethod
    async def run(socket, path, services):
        message = await socket.recv()
        print(message)
        #await socket.send(message)
        uri = 'ws://127.0.0.1:7012/chat'
        async with websockets.connect(uri) as websocket:
            print('forwarding to UI...')
            await websocket.send(message)
