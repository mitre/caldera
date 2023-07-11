import itertools
import glob
import re
from base64 import b64decode
from importlib import import_module

from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_link import update_scores
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
        await update_scores(operation=None, increment=len(found_facts), used=facts, facts=link.facts)
        await self._store_results(link, found_facts, operation)

    async def _store_results(self, link, facts, operation=None):
        facts_covered = []
        for relationship in self.model:
            matches = []
            for fact in facts:
                if fact.trait in relationship:
                    matches.append(fact)
                    facts_covered.append(fact)
            for pair in itertools.combinations(matches, r=2):
                if pair[0].trait != pair[1].trait:
                    await link.create_relationships([Relationship(source=pair[0], edge='has', target=pair[1])],
                                                    operation=operation)
        for f in [x for x in facts if x not in facts_covered]:
            await link.save_fact(operation=operation, fact=f, score=1, relationship=[])
