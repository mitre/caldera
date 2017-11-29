from unittest import TestCase
from caldera.app import ddp
import ujson as json


class TestCollection(object):
    def register_callcollectionname(self):
        pass


class TestParser(TestCase):
    def testNbtstat(self):
        result = []
        collection = object
        write = lambda x: result.append(x)
        ddps = ddp.DDPServer(write)
        # connect
        msg = json.dumps({"msg": "connect"})
        ddps.parse_message(msg)
        r = result.pop(0)
        self.assertEqual(result, [])
        self.assertEqual(json.loads(r), {"msg": "connected", "session": "1"})
        # subscribe
        msg = json.dumps({"msg": "sub", "name": "collectionname", "id": "1"})
        ddps.parse_message(msg)
        r = result.pop(0)
        self.assertEqual(result, [])
        self.assertEqual(json.loads(r), {"msg": "connected", "session": "1"})
