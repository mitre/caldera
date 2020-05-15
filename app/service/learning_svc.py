import itertools
import glob
import re
from base64 import b64decode
from importlib import import_module

from app.objects.secondclass.c_relationship import Relationship
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
            if ability.test:
                variables = frozenset(re.findall(self.re_variable, self.decode_bytes(ability.test)))
                if len(variables) > 1:  # relationships require at least 2 variables
                    self.model.add(variables)
        self.model = set(self.model)

    async def learn(self, facts, link, blob):
        decoded_blob = b64decode(blob).decode('utf-8')

        found_facts = []
        for parser in self.parsers:
            try:
                for fact in parser.parse(decoded_blob):
                    await self._save_fact(link, facts, fact)
                    found_facts.append(fact)
            except Exception as e:
                self.log.error(e)
        await self._update_scores(link, facts, increment=len(found_facts))
        await self._build_relationships(link, found_facts)

    """ PRIVATE """

    @staticmethod
    async def _update_scores(link, facts, increment):
        for uf in link.facts:
            for found_fact in facts:
                if found_fact.unique == uf.unique:
                    found_fact.score += increment
                    break

    @staticmethod
    async def _save_fact(link, facts, fact):
        if all(fact.trait) and not any(f.trait == fact.trait and f.value == fact.value for f in facts):
            fact.collected_by = link.paw
            fact.technique_id = link.ability.technique_id
            link.facts.append(fact)

    async def _build_relationships(self, link, facts):
        for relationship in self.model:
            matches = []
            for fact in facts:
                if fact.trait in relationship:
                    matches.append(fact)
            for pair in itertools.combinations(matches, r=2):
                if pair[0].trait != pair[1].trait:
                    link.relationships.append(Relationship(source=pair[0], edge='has', target=pair[1]))
