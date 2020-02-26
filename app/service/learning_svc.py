import glob
from base64 import b64decode
from importlib import import_module

from app.utility.base_service import BaseService


class LearningService(BaseService):

    def __init__(self):
        self.log = self.add_service('learning_svc', self)
        self.parsers = self.add_parsers('app/learning')
        self.log.debug('Loaded %d parsers' % len(self.parsers))

    @staticmethod
    def add_parsers(directory):
        parsers = []
        for filepath in glob.iglob('%s/**.py' % directory):
            module = import_module(filepath.replace('/', '.').replace('\\', '.').replace('.py', ''))
            parsers.append(getattr(module, 'Parser')())
        return parsers

    async def learn(self, link, blob):
        decoded_blob = b64decode(blob).decode('utf-8')
        operation = (await self.get_service('data_svc').locate('operations', dict(id=link.operation)))[0]

        found_facts = 0
        for parser in self.parsers:
            try:
                for fact in parser.parse(decoded_blob):
                    await self._save_fact(link, operation, fact)
                    found_facts += 1
            except Exception as e:
                self.log.error(e)
        await self._update_scores(link, operation, increment=found_facts)

    """ PRIVATE """

    @staticmethod
    async def _update_scores(link, operation, increment):
        for uf in link.facts:
            for found_fact in operation.all_facts():
                if found_fact.unique == uf.unique:
                    found_fact.score += increment
                    break

    @staticmethod
    async def _save_fact(link, operation, fact):
        if all(fact.trait) and not any(f.trait == fact.trait and f.value == fact.value for f in operation.all_facts()):
            fact.collected_by = link.paw
            fact.technique_id = link.ability.technique_id
            link.facts.append(fact)
