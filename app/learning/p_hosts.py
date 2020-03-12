import re

from app.objects.secondclass.c_fact import Fact


class Parser:

    def __init__(self):
        self.trait = 'multiple'  # remote.host.name, remote.host.fqdn

    def parse(self, blob):
        for p in re.findall(r'dnshostname[\s:]*(.*?)[\r\n]', blob):
            yield Fact(trait='remote.host.fqdn', value=p)
        for p in re.findall(r'cn[\s:]*(.*?)[\r\n]', blob):
            yield Fact(trait='remote.host.name', value=p)
        for p in re.findall(r'\\\\(.*?)\\', blob):
            yield Fact(trait='remote.host.name', value=p)
