import asyncio
import json
import websockets

from app.service.interfaces.i_event_svc import EventServiceInterface
from app.utility.base_service import BaseService


class EventService(EventServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('event_svc', self)
        self.contact_svc = self.get_service('contact_svc')
        self.ws_uri = 'ws://{}'.format(self.get_config('app.contact.websocket'))

    async def observe_event(self, event, callback):
        ws_contact = [c for c in self.contact_svc.contacts if c.name == 'websocket']
        handle = _Handle(event, callback)
        ws_contact[0].handler.handles.append(handle)

    async def fire_event(self, event, **callback_kwargs):
        uri = '{}/{}'.format(self.ws_uri, event)
        msg = json.dumps(callback_kwargs)
        loop = asyncio.get_event_loop()
        async with websockets.connect(uri) as websocket:
            loop.create_task(websocket.send(msg))


class _Handle:

    def __init__(self, tag, callback):
        self.tag = tag
        self.callback = callback

    async def run(self, socket, path, services):
        return await self.callback(socket, path, services)
