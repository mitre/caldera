# server side implementation of a data replication protocol loosely based on DDP
# https://github.com/meteor/meteor/blob/devel/packages/ddp/DDP.md
import ujson as json
import logging
import asyncio
from .engine.database import native_types
import functools
import time
from bson.codec_options import CodecOptions
from bson.raw_bson import RawBSONDocument
from pymongo.cursor import CursorType
import bson as bson


log = logging.getLogger(__name__)


class DDPServer(object):
    def __init__(self, write):
        self._parse = {"connect": self._connect,
                       "sub": self._sub,
                       "method": self._method,
                       "ping": self._ping,
                       "unsub": self._unsub,
                       }

        self._methods = {}
        self._collections = {}
        self._subscriptions = {}
        self._write = write
        self.counter = 0

    def write(self, x, unsafe=False):
        t1 = time.process_time()
        if not unsafe:
            x = native_types(x)
        t2 = time.process_time()
        bs = bson.BSON.encode(x)
        t3 = time.process_time()
        self._write(bs)
        t4 = time.process_time()
        return t2 - t1, t3 - t2, t4 - t3

    def parse_message(self, msg):
        if isinstance(msg, str):
            m = json.loads(msg)
        else:
            m = bson.BSON.decode(msg)
        if 'msg' in m:
            p = self._parse[m['msg']]
            m.pop('msg')
            p(**m)

    def _unsub(self, id):
        try:
            task, unsub = self._subscriptions[id]
            unsub()
            task.cancel()
            del self._subscriptions[id]
        except KeyError:
            pass

    def _sub(self, name, id):
        try:
            # get the collection
            collection = self._collections[name]

            # register callback into database
            # Note this is done explicitly before querying the database to avoid race conditions for object updates
            q = asyncio.Queue()
            collection.subscribe(q)

            # write everything in the collection
            bson_col = collection._get_collection().with_options(codec_options=CodecOptions(document_class=RawBSONDocument))
            wt = 0
            nt = 0
            jt = 0
            wwt = 0
            ct = 0
            tt1 = time.process_time()
            ct0 = time.process_time()
            for o in bson_col.find(cursor_type=CursorType.EXHAUST):
                ct1 = time.process_time()
                ct += ct1 - ct0
                wt1 = time.process_time()
                nt0, jt0, wwt0 = self.write({"msg": "insert", "collection": name, "bson": o.raw}, unsafe=True)
                wt2 = time.process_time()
                wt += wt2 - wt1
                nt += nt0
                jt += jt0
                wwt += wwt0
                ct0 = time.process_time()

            tt2 = time.process_time()
            if tt2 -tt1 > 0.1:
                log.info("Total time for '{}': {}s\n  collection time: {}s\n  write time: {}s\n    native time: {}s\n    json time: {}s\n    wwrite time: {}s".format(bson_col.full_name, tt2 - tt1, ct, wt, nt, jt, wwt))

            self.write({"msg": "ready", "id": id})

            loop = asyncio.get_event_loop()
            task = loop.create_task(self._subscriber(name, q))
            self._subscriptions[id] = (task, functools.partial(collection.unsubscribe, q))
        except KeyError:
            pass

    # Get
    async def _subscriber(self, collection_name, queue):
        while True:
            method, obj = await queue.get()
            try:
                if method == "d":
                    self.write({"msg": "removed", "collection": collection_name, "id": obj['_id']}, unsafe=True)
                else:
                    self.write({"msg": "changed", "collection": collection_name, "id": obj['_id'], "fields": obj}, unsafe=True)
            except RuntimeError:
                # websocket closed
                log.debug("Websocket closed")
                try:
                    collection = self._collections[collection_name]
                    collection.unsubscribe(queue)
                except KeyError:
                    pass
                finally:
                    return

    def _method(self, m):
        try:
            method = m['method']
            params = m['params']
        except KeyError:
            return
        try:
            callback = self._methods[method]
            ret = callback(*params)
            m.write({"msg": "result", "result": ret})
        except KeyError:
            log.warning("DDP unknown method: '{}'".format(method))

    def _ping(self):
        self.write({"msg": "pong"})

    def _connect(self):
        self.write({"msg": "connected", "session": str(self.counter)})
        self.counter += 1

    def register_method(self, name, callback):
        self._methods[name] = callback

    def register_collection(self, name, collection):
        self._collections[name] = collection
