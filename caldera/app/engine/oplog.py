import pymongo
import logging
import queue
import asyncio
import threading
from collections import defaultdict
from .. import util


log = logging.getLogger(__name__)


class OplogTailer(object):
    def __init__(self, host, port):
        # create the callback
        self.host = host
        self.port = port
        self.queue = queue.Queue()
        self.subs = {}

    def start(self):
        t = threading.Thread(target=self.tail, args=(self.queue, self.host, self.port), daemon=True)
        t.start()

    # designed to be run in its own thread
    # coroutine_callback must be threadsafe
    @staticmethod
    def tail(com_queue, host, port):
        oplog = pymongo.MongoClient(host, port).local.oplog.rs
        ts = next(oplog.find().sort('$natural', pymongo.DESCENDING).limit(-1))['ts']
        namespace_notifies = defaultdict(list)
        wait_namespace_notifies = defaultdict(list)
        id_notifies = defaultdict(list)

        while True:
            cursor = oplog.find({'ts': {'$gt': ts}}, cursor_type=pymongo.CursorType.TAILABLE_AWAIT, oplog_replay=True)
            while cursor.alive:
                for doc in cursor:
                    ts = doc['ts']
                    # update the filters
                    try:
                        while True:
                            typ, blob = com_queue.get_nowait()
                            if typ == "wait":
                                cb, namespace, query = blob
                                id = query.get("_id", None)
                                if id:
                                    id_notifies[id].append((query, cb))
                                else:
                                    wait_namespace_notifies[namespace].append((query, cb))
                            elif typ == "sub":
                                cb, namespace, query = blob
                                namespace_notifies[namespace].append((query, cb))
                            elif typ == "unsub":
                                cb = blob
                                for k, elem in namespace_notifies.items():
                                    namespace_notifies[k] = [x for x in elem if x[1] != cb]
                    except queue.Empty:
                        pass

                    # check for a match in the filters
                    id = None
                    if doc["op"] == "u":
                        id = doc['o2']["_id"]
                        c = doc["o"]['$set']
                        c['_id'] = id
                    elif doc["op"] == "i":
                        if '_id' in doc['o']:
                            id = doc['o']['_id']
                        c = doc['o']
                    elif doc["op"] == "d":
                        id = doc['o']['_id']
                        c = doc['o']

                    namespace = doc["ns"]
                    if doc["op"] == "d":
                        for query, cb in namespace_notifies[namespace]:
                            if util.nested_cmp(c, query):
                                cb("d", c)

                    if doc["op"] in ("u", "i"):
                        for query, cb in namespace_notifies[namespace]:
                            if util.nested_cmp(c, query):
                                cb("u", c)

                        # perform check on id_notifies
                        if id:
                            check, nocheck = [], []
                            [check.append(x) if util.nested_cmp(c, x[0]) else nocheck.append(x) for x in id_notifies[id]]
                            id_notifies[id] = nocheck
                            [x[1]("u", c) for x in check]

                            # perform check on the collection waits
                            check, nocheck = [], []
                            [check.append(x) if util.nested_cmp(c, x[0]) else nocheck.append(x) for x in wait_namespace_notifies[namespace]]
                            wait_namespace_notifies[namespace] = nocheck
                            [x[1]("u", c) for x in check]

            log.warning("Mongo oplog cursor exited")

    @staticmethod
    def _get_cb(q, loop):
        def t(*args):
            async def ret():
                await q.put(args)

            asyncio.run_coroutine_threadsafe(ret(), loop)
        return t

    async def wait(self, namespace: str, query: dict):
        # threadsafe
        loop = asyncio.get_event_loop()
        tqueue = asyncio.Queue()
        cb = self._get_cb(tqueue, loop)
        # push onto the queue
        self.queue.put(("wait", (cb, namespace, query)))
        # wait for it
        return await tqueue.get()

    def subscribe(self, namespace: str, q):
        """
        Subscribe to all changes on a collection
        """
        # threadsafe
        loop = asyncio.get_event_loop()
        cb = self._get_cb(q, loop)
        self.subs[q] = cb
        # push onto the queue
        self.queue.put(("sub", (cb, namespace, {})))

    def unsubscribe(self, q):
        """
        Unsubscribe the queue to changes on a collection
        """
        # push onto the queue
        self.queue.put(("unsub", (self.subs[q])))
