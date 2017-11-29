import logging
from cryptography.fernet import Fernet
from mongoengine import connect, Document
from mongoengine.base import TopLevelDocumentMetaclass, BaseDocument
from mongoengine.queryset.base import BaseQuerySet
from bson.objectid import ObjectId
import ujson as json
import pymongo
from .oplog import OplogTailer
import base64
from typing import Dict
import asyncio


log = logging.getLogger(__name__)

key = None
global_tailer = None

db_name = "virts"
replica_set_name = "caldera"


def _setup_replica_set(host, port) -> None:
    """
    Sets up a replica set on a MongoDB instance
    Args:
        host: MongoDB host
        port: MongoDB port
    """
    config = {'_id': replica_set_name, 'members': [{'_id': 0, 'host': '{}:{}'.format(host, port)}]}
    c = pymongo.MongoClient(host, port)
    c.admin.command("replSetInitiate", config)


def initialize(db_key, host, port) -> None:
    """
    Sets up the database, safe to be called before fork()ing

    Args:
        db_key: Keys used to encrypt and decrypt database entries
        host: the host of the database
        port: the port of the database
    """
    global key
    key = db_key
    client = None
    try:
        client = pymongo.MongoClient(host, port)
        oplog = client.local.oplog.rs
        a = next(oplog.find().sort('$natural', pymongo.DESCENDING).limit(-1))['ts']
    except StopIteration:
        log.info("Performing first time replication set initialization on MongoDB")
        _setup_replica_set(host, port)
    finally:
        if client is not None:
            client.close()


def start(host, port) -> None:
    """
    Starts the database connection and the global oplog tailer. It should only be called after fork()ing

    Args:
        host: the database host
        port: the database port

    Returns:
        Nothing
    """
    global global_tailer
    global_tailer = OplogTailer(host, port)
    global_tailer.start()
    connect(db_name, replicaSet=replica_set_name, tz_aware=True, host=host, port=port)


class ExtrovirtsDocumentMeta(TopLevelDocumentMetaclass):
    def __new__(mcs, name, bases, dct):
        return super().__new__(mcs, name, bases, dct)


class ExtrovirtsDocument(Document, metaclass=ExtrovirtsDocumentMeta):
    meta = {
        'abstract': True,
    }

    def __str__(self):
        return str(self.to_dict())

    def to_json(self) -> str:
        """
        Converts this document to json
        Returns:
            The converted document as json
        """
        return json.dumps(native_types(self), sort_keys=True, indent=4)

    def to_dict(self, dbref: bool=False) -> Dict:
        """
        Converts this document to a dictionary
        Args:
            dbref: If true, convert ObjectIds to DBRefs

        Returns:
            The converted document as a dictionary
        """
        dictified = self.to_mongo().to_dict()
        if dbref:
            for field, value in dictified.items():
                if isinstance(value, ObjectId) and field != '_id':
                    t = getattr(self, field)
                    if isinstance(t, ObjectId):
                        t = t.to_dbref()
                    dictified[field] = t

        return dictified

    def get(self, k, default=None):
        return self[k] if k in self else default

    async def wait(self, filters: Dict=None) -> 'ExtrovirtsDocument':
        """
        Wait for the object to be modified and have the expected criteria.
        This is implemented with asyncio futures. The future is created here
        and then added to the list (in self.futures), which can be accessed
        globally by any other more up-to-date versions of this object. When
        the state is as expected

        Args:
            filters: A dictionary containing key value pairs that the state should be waited on

        Returns:
            self
        """
        log.debug("{} waiting on filters {}".format(self, filters))
        if not filters:
            filters = {}
        filters.update({'_id': self.id})
        await global_tailer.wait(self._get_collection().full_name, filters)
        log.debug("Object {}({}) woken up".format(type(self).__name__, self.id))
        # Return self to allow for chaining
        self.reload()
        return self

    @classmethod
    async def wait_next(cls, filters: Dict=None) -> 'ExtrovirtsDocument':
        """
        Wait for an object to be created that matches the criteria.
        Assumes that the database has already been checked and no
        objects were found. Now need to wait for object changes to match

        Args:
            filters: the filters (if any) representing the state of the object to wait for

        Returns:
            The document fulfilling the filters
        """
        log.debug("Newly waiting on {}({})".format(cls.__name__, filters))
        if not filters:
            filters = {}
        _, c = await global_tailer.wait(cls._get_collection().full_name, filters)
        log.debug("{} woken up".format(cls.__name__))
        return cls.objects.with_id(c["_id"])

    @classmethod
    def subscribe(cls, queue: asyncio.Queue) -> None:
        """
        Subscribe to all changes on a collection

        Args:
            queue: A queue that updates will be pushed to
        """
        log.debug("Subscribe to {}".format(cls.__name__))
        global_tailer.subscribe(cls._get_collection().full_name, queue)

    @classmethod
    def unsubscribe(cls, queue: asyncio.Queue) -> None:
        """
        Unsubscribe to changes on a collection

        Args:
            queue: the queue that will be unsubscribed from updates.
        """
        log.debug("Unsubscribe to {}".format(cls.__name__))
        global_tailer.unsubscribe(queue)


def native_types(obj):
    """
    Converts an object to a json serializable type
    Args:
        obj: An object

    Returns:
        A JSON serializable type
    """
    if isinstance(obj, BaseDocument):
        obj = obj.to_dict()
    elif isinstance(obj, BaseQuerySet):
        obj = list(obj)
    elif isinstance(obj, ObjectId):
        obj = str(obj)
    elif hasattr(obj, 'isoformat'):
        obj = obj.isoformat()
    if isinstance(obj, dict):
        return {native_types(k): native_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [native_types(x) for x in obj]
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode('ascii')
    return obj


def subjectify(item):
    if isinstance(item, list):
        for i, sub_item in enumerate(item):
            item[i] = subjectify(sub_item)
    elif isinstance(item, dict):
        for k, v in item.items():
            item[k] = subjectify(v)
    elif isinstance(item, ObjectId):
        item = str(item)
    return item


class CustomSerializer(object):
    def serialize(self, value):
        pass

    def deserialize(self, value):
        pass


def serialize(item, serializers):
    for k, v in serializers.items():
        try:
            base = item
            parts = k.split('.')
            parents = parts[:-1] if len(parts) > 1 else []
            last = parts[-1]
            for attr in parents:
                base = base[attr]
            if isinstance(base, list):
                for i in base:
                    i[last] = v().serialize(i[last])
            else:
                base[last] = v().serialize(base[last])
        except KeyError:
            pass
    return item


def deserialize(item, serializers):
    for k, v in serializers.items():
        try:
            base = item
            parts = k.split('.')
            parents = parts[:-1] if len(parts) > 1 else []
            last = parts[-1]
            for attr in parents:
                base = base[attr]
            if isinstance(base, list):
                for i in base:
                    i[last] = v().deserialize(i[last])
            else:
                base[last] = v().deserialize(base[last])
        except KeyError:
            pass
    return item


class EncryptedValue(CustomSerializer):
    def __init__(self):
        self.fernet = Fernet(key)

    def serialize(self, value):
        return self.fernet.encrypt(value.encode())

    def deserialize(self, value):
        return self.fernet.decrypt(value).decode()
