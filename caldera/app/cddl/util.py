from collections import defaultdict
import re
import string
from typing import TypeVar, Generic, List, Iterable, Union, Sequence, Dict


T = TypeVar('T')


class CaseException(Exception):
    pass


class Trie(Generic[T]):
    def __init__(self, item: Sequence[T]=None) -> None:
        self.children = defaultdict(Trie) # type: Dict[T, Trie]
        if item:
            self.add_item(item)

    def add_item(self, item: Sequence[T]) -> None:
        if item:
            self.children[item[0]].add_item(item[1:])

    def breadth_traverse(self) -> Iterable[List[T]]:
        for key in self.children.keys():
            yield [key]
        for key, child in self.children.items():
            for i in child.breadth_traverse():
                yield [key] + i

    def __iter__(self):
        for key, child in self.children.items():
            yield [key]
            for i in child:
                yield [key] + i


class DotTrie(Trie):
    def add_item(self, item):
        if item:
            super().add_item(item.split('.'))

    def __iter__(self):
        for i in super():
            yield '.'.join(i)


# convert steps to logic predicates
class Variable(object):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __lt__(self, other):
        return str(self) < str(other)


class Term(object):
    def __str__(self):
        return "{}({})".format(self.predicate, ", ".join([str(x) for x in self.literals]))

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

    def __lt__(self, other):
        return str(self) < str(other)

    def __init__(self, name: str, *literals: Union[None, Iterable[str]]) -> None:
        if not literals:
            self.predicate = self._predicate(name)
            self.literals = self._literals(name)
        else:
            self.predicate = name
            self.literals = list(literals)

    @property
    def all(self):
        return [self.predicate] + self.literals

    @staticmethod
    def _predicate(term: str):
        match = re.search(r"(.*)\(", term)
        if match is not None:
            return match.group(1)
        else:
            return term

    @staticmethod
    def _literals(term: str):
        match = re.search(r".*\((.*)\)", term)
        if match is not None:
            literals = match.group(1)
            return [x.strip() for x in literals.split(",")]
        else:
            return []


def string_generator(num):
    accum = ""

    while True:
        accum = string.ascii_lowercase[num % 26] + accum
        num //= 26
        if num == 0:
            return accum
