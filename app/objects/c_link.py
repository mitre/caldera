from base64 import b64decode
from datetime import datetime
from importlib import import_module

from app.utility.base_object import BaseObject
from app.objects.c_fact import Fact


class Link(BaseObject):

    @property
    def unique(self):
        return self.id

    @property
    def display(self):
        return self.clean(dict(id=self.id, operation=self.operation, paw=self.paw, command=self.command,
                               executor=self.ability.executor, status=self.status, score=self.score,
                               decide=self.decide.strftime('%Y-%m-%d %H:%M:%S'),
                               facts=[fact.display for fact in self.facts],
                               collect=self.collect.strftime('%Y-%m-%d %H:%M:%S') if self.collect else '',
                               finish=self.finish, ability=self.ability.display, cleanup=self.cleanup))

    def __init__(self, operation, command, paw, ability, status, score=0, jitter=0, cleanup=0):
        self.id = None
        self.command = command
        self.operation = operation
        self.paw = paw
        self.cleanup = cleanup
        self.ability = ability
        self.status = status
        self.score = score
        self.jitter = jitter
        self.decide = datetime.now()
        self.pid = None
        self.collect = None
        self.finish = None
        self.facts = []
        self.relationships = []
        self.used = []

    async def parse(self, operation):
        try:
            with open('data/results/%s' % int(float(self.id)), 'r') as fle:
                for parser in self.ability.parsers:
                    if self.status != 0:
                        continue
                    relationships = await self._parse_link_result(fle.read(), parser)
                    await self._update_scores(operation, increment=len(relationships))
                    await self._create_relationships(relationships, operation)
        except Exception as e:
            print(e)

    """ PRIVATE """

    async def _parse_link_result(self, result, parser):
        blob = b64decode(result).decode('utf-8')
        parser_info = dict(module=parser.module, used_facts=self.used, mappers=parser.relationships)
        p_inst = await self._load_module('Parser', parser_info)
        try:
            return p_inst.parse(blob=blob)
        except Exception as e:
            return []

    @staticmethod
    async def _load_module(module_type, module_info):
        module = import_module(module_info['module'])
        return getattr(module, module_type)(module_info)

    async def _create_relationships(self, relationships, operation):
        for relationship in relationships:
            await self._save_fact(operation, relationship.source)
            await self._save_fact(operation, relationship.target)
            self.relationships.append(relationship)

    async def _save_fact(self, operation, prop):
        if not any(f.prop == prop[0] and f.value == prop[1] for f in operation.all_facts()):
            self.facts.append(Fact(prop=prop[0], value=prop[1], score=1))

    async def _update_scores(self, operation, increment):
        for uf in self.used:
            for found_fact in operation.all_facts():
                if found_fact.unique == uf.unique:
                    found_fact.score += increment
                    break

