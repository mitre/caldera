import asyncio
import datetime
import json
import websockets

from app.service.interfaces.i_event_svc import EventServiceInterface
from app.utility.base_service import BaseService


class EventService(EventServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('event_svc', self)
        self.contact_svc = self.get_service('contact_svc')
        self.ws_uri = 'ws://{}'.format(self.get_config('app.contact.websocket'))
        self.default_exchange = 'caldera'
        self.default_queue = 'general'

    async def observe_event(self, callback, exchange=None, queue=None):
        exchange = exchange or self.default_exchange
        queue = queue or self.default_queue
        path = '/'.join([exchange, queue])
        handle = _Handle(path, callback)
        ws_contact = await self.contact_svc.get_contact('websocket')
        ws_contact.handler.handles.append(handle)

    async def handle_exceptions(self, awaitable):
        try:
            return await awaitable
        except websockets.exceptions.ConnectionClosedOK:
            pass  # No handler was registered for this event
        except Exception as e:
            self.log.error("WebSocket error: {}".format(e), exc_info=True)

    async def fire_event(self, exchange=None, queue=None, timestamp=True, **callback_kwargs):
        exchange = exchange or self.default_exchange
        queue = queue or self.default_queue
        metadata = {}
        if timestamp:
            metadata.update(dict(timestamp=datetime.datetime.now().timestamp()))
        callback_kwargs.update(dict(metadata=metadata))
        uri = '/'.join([self.ws_uri, exchange, queue])
        msg = json.dumps(callback_kwargs)
        async with websockets.connect(uri) as websocket:
            asyncio.get_event_loop().create_task(self.handle_exceptions(websocket.send(msg)))


class _Handle:

    def __init__(self, tag, callback):
        self.tag = tag
        self.callback = callback

    async def run(self, socket, path, services):
        return await self.callback(socket, path, services)
