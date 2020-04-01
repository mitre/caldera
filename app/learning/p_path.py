import re

from app.objects.secondclass.c_fact import Fact


class Parser:

    def __init__(self):
        self.trait = 'host.file.path'

    def parse(self, blob):
        for p in re.findall(r'(\/.*?\.[\w:]+[^\s]+)', blob):
            yield Fact.load(dict(trait=self.trait, value=p))
        for p in re.findall(r'(C:\\.*?\.[\w:]+)', blob):
            yield Fact.load(dict(trait=self.trait, value=p))
