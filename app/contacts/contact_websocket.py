import asyncio
import json
import websockets
import inspect

from datetime import datetime, timezone

from app.service.interfaces.i_event_svc import EventServiceInterface
from app.utility.base_service import BaseService


class EventService(EventServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('event_svc', self)
        self.contact_svc = self.get_service('contact_svc')

        # Ensure WebSocket URI is properly configured
        try:
            ws_config = self.get_config('app.contact.websocket')
            if not ws_config:
                raise ValueError("WebSocket URI is not properly configured.")
            self.ws_uri = f'ws://{ws_config}'
        except Exception as e:
            self.log.error(f"Error setting WebSocket URI: {e}", exc_info=True)
            self.ws_uri = 'ws://localhost:8888'  # Fallback URI

        self.global_listeners = []
        self.default_exchange = 'caldera'
        self.default_queue = 'general'

    async def observe_event(self, callback, exchange=None, queue=None):
        """
        Register a callback for a specific event. The callback is triggered 
        when an event of the specified type occurs.

        :param callback: Callback function
        :param exchange: Event exchange (default: caldera)
        :param queue: Event queue (default: general)
        """
        exchange = exchange or self.default_exchange
        queue = queue or self.default_queue
        path = '/'.join([exchange, queue])
        handle = _Handle(path, callback)
        ws_contact = await self.contact_svc.get_contact('websocket')
        ws_contact.handler.handles.append(handle)

    async def register_global_event_listener(self, callback):
        """
        Register a global event listener that triggers whenever any event occurs.

        :param callback: Callback function
        """
        self.global_listeners.append(callback)

    async def notify_global_event_listeners(self, event, **callback_kwargs):
        """
        Notify all registered global event listeners when an event is triggered.

        :param event: Event string (format: '<exchange>/<queue>')
        """
        for callback in self.global_listeners:
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(event, **callback_kwargs)
                else:
                    callback(event, **callback_kwargs)
            except Exception as e:
                self.log.error(f"Error in global callback: {e}", exc_info=True)

    async def handle_exceptions(self, awaitable):
        """
        Handle WebSocket exceptions to prevent crashes.
        """
        try:
            return await awaitable
        except websockets.exceptions.ConnectionClosedOK:
            pass  # No handler was registered for this event
        except Exception as e:
            self.log.error(f"WebSocket error: {e}", exc_info=True)

    async def fire_event(self, exchange=None, queue=None, timestamp=True, **callback_kwargs):
        """
        Fire an event to the WebSocket server.

        :param exchange: Exchange name (default: caldera)
        :param queue: Queue name (default: general)
        :param timestamp: Include timestamp in event metadata (default: True)
        """
        exchange = exchange or self.default_exchange
        queue = queue or self.default_queue
        metadata = {}
        if timestamp:
            metadata['timestamp'] = datetime.now(timezone.utc).timestamp()
        callback_kwargs['metadata'] = metadata
        uri = '/'.join([self.ws_uri, exchange, queue])

        if self.global_listeners:
            asyncio.create_task(
                self.notify_global_event_listeners('/'.join([exchange, queue]), **callback_kwargs)
            )

        d = json.dumps(callback_kwargs)
        try:
            async with websockets.connect(uri) as websocket:
                asyncio.create_task(self.handle_exceptions(websocket.send(d)))
                await asyncio.sleep(0)  # Yield control to the event loop
        except Exception as e:
            self.log.error(f"Failed to connect to WebSocket server at {uri}: {e}", exc_info=True)


class _Handle:

    def __init__(self, tag, callback):
        self.tag = tag
        self.callback = callback

    async def run(self, socket, path, services):
        return await self.callback(socket, path, services)
