import itertools
import glob
import re
from base64 import b64decode
from importlib import import_module

from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_fact import OriginType
from app.service.interfaces.i_learning_svc import LearningServiceInterface
from app.utility.base_service import BaseService


class LearningService(LearningServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('learning_svc', self)
        self.model = set()
        self.parsers = self.add_parsers('app/learning')
        self.re_variable = re.compile(r'#{(.*?)}', flags=re.DOTALL)
        self.log.debug('Loaded %d parsers' % len(self.parsers))

    @staticmethod
    def add_parsers(directory):
        parsers = []
        for filepath in glob.iglob('%s/**.py' % directory):
            module = import_module(filepath.replace('/', '.').replace('\\', '.').replace('.py', ''))
            parsers.append(module.Parser())
        return parsers

    async def build_model(self):
        for ability in await self.get_service('data_svc').locate('abilities'):
            for executor in ability.executors:
                if executor.command:
                    variables = frozenset(re.findall(self.re_variable, executor.test))
                    if len(variables) > 1:  # relationships require at least 2 variables
                        self.model.add(variables)
        self.model = set(self.model)

    async def learn(self, facts, link, blob, operation=None):
        decoded_blob = b64decode(blob).decode('utf-8')

        found_facts = []
        for parser in self.parsers:
            try:
                for fact in parser.parse(decoded_blob):
                    found_facts.append(fact)
            except Exception as e:
                self.log.error(e)
        await self._update_scores(link, facts, increment=len(found_facts))
        await self._build_relationships(link, found_facts, operation)

    """ PRIVATE """

    @staticmethod
    async def _update_scores(link, facts, increment):
        knowledge_svc_handle = BaseService.get_service('knowledge_svc')
        for uf in link.facts:
            for found_fact in facts:
                if found_fact.unique == uf.unique:
                    found_fact.score += increment
                    knowledge_svc_handle.update_fact(dict(trait=found_fact.trait, value=found_fact.value,
                                                          source=found_fact.source), dict(score=found_fact.score))
                    break

    @staticmethod
    async def _save_fact(link, facts, fact, operation=None):
        if all(fact.trait) and not any(f.trait == fact.trait and f.value == fact.value and f.source == link.id
                                       for f in facts):
            fact.collected_by = link.paw
            fact.technique_id = link.ability.technique_id
            fact.links = [link]
            fact.relationships = []
            fact.source_type = OriginType.LEARNED.name
            fact.source = operation.id if operation else link.id
            knowledge_svc_handle = BaseService.get_service('knowledge_svc')
            await knowledge_svc_handle.add_fact(fact)
            link.facts.append(fact)

    async def _build_relationships(self, link, facts, operation=None):
        facts_covered = []
        for relationship in self.model:
            matches = []
            for fact in facts:
                if fact.trait in relationship:
                    matches.append(fact)
                    facts_covered.append(fact)
                else:
                    await self._save_fact(link, facts, fact)
            for pair in itertools.combinations(matches, r=2):
                if pair[0].trait != pair[1].trait:
                    await link._create_relationships([Relationship(source=pair[0], edge='has', target=pair[1])],
                                                     operation=operation)
        # make sure we always record all the facts, even if there isn't a model set, or it would slip through otherwise
        for f in [x for x in facts if x not in facts_covered]:
            await self._save_fact(link, facts, f, operation)
