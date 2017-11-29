from collections import defaultdict
from typing import Iterable, Set, List, Union
from caldera.app.logic.logic import Term, Action, Variable
from caldera.app.util import CaseException
from unification import unify, var, unifiable
import itertools


def make_unifiable(obj: object, var_func=var) -> object:
    if isinstance(obj, list):
        return [make_unifiable(x, var_func=var_func) for x in obj]
    elif isinstance(obj, Term):
        return Term(obj.predicate, *[make_unifiable(x, var_func=var_func) for x in obj.literals])
    elif isinstance(obj, Variable):
        return var_func(obj.name)
    elif isinstance(obj, tuple):
        return tuple(make_unifiable(x, var_func=var_func) for x in obj)
    else:
        return obj


def convert_value_var_to_static(term: Term) -> Term:
    if len(term.literals) == 3:
        if isinstance(term.literals[2], Variable):
            return Term(term.predicate, term.literals[0], term.literals[1], "__var__" + term.literals[2].name)
    return term


def get_fresh(action: Action):
    add_objects = []
    for add in action.add:
        if isinstance(add, Term) and len(add.literals) == 1:
            add_objects.append(add)

    add_props = defaultdict(list)
    for add in action.add:
        if isinstance(add, Term) and len(add.literals) != 1:
            add_props[add.literals[0]].append(add)

    req_objects = []
    for req in action.requirements:
        if isinstance(req, Term) and len(req.literals) == 1:
            req_objects.append(req)

    req_props = defaultdict(list)
    for req in action.requirements:
        if isinstance(req, Term) and len(req.literals) != 1:
            req_props[req.literals[0]].append(req)

    null_props = []
    for add_object in add_objects:
        for req_object in req_objects:
            if add_object.predicate == req_object.predicate:
                # find the freshness
                for req_prop in req_props[req_object.literals[0]]:
                    # does it unify with an add prop?
                    for add_prop in add_props[add_object.literals[0]]:
                        if unify(make_unifiable(convert_value_var_to_static(add_prop)),
                                 make_unifiable(convert_value_var_to_static(req_prop))):
                            # then nullify the add prop
                            null_props.append(add_prop)

    return list(set(action.add) - set(null_props))


@unifiable
class Node(object):
    def __init__(self, content) -> None:
        self.content = content

    def __repr__(self):
        return repr(self.content)


class DiGraph(object):
    def __init__(self):
        self.nodes = []
        self.edge_set = set()

    def add_node(self, node: Node) -> None:
        self.nodes.append(node)

    def add_nodes(self, nodes: Iterable[Node]) -> None:
        for node in nodes:
            self.nodes.append(node)

    def add_edge(self, from_node: Node, to_node: Node):
        self.edge_set.add((from_node, to_node))

    def unify_node(self, contents) -> Union[Node, None]:
        for node in self.nodes:
            unification = unify(make_unifiable(contents), make_unifiable(node.content))
            if unification:
                return node, unification

        return None, None

    def unify_nodes(self, combine_func):
        unifications = defaultdict(set)
        for node1, node2 in itertools.combinations(self.nodes, 2):
            assert node1 != node2
            unity = unify(make_unifiable(node1.content), make_unifiable(node2.content))
            if unity or unity == {}:
                unifications[node1].add(node2)

        for node1, node_set in unifications.items():
            for node2 in node_set:
                if node1 in self.nodes and node2 in self.nodes:
                    self.combine_nodes(node1, node2, combine_func)

    def compress_nodes(self, nodes: Iterable[Node], combine_func) -> None:
        node_list = list(nodes)
        changed = True
        while changed:
            changed = False
            for node1, node2 in itertools.combinations(node_list, 2):
                neighbors1 = self.get_neighbors(node1)
                if neighbors1 and neighbors1 == self.get_neighbors(node2):
                    self.combine_nodes(node1, node2, combine_func)
                    changed = True
                    node_list.remove(node2)
                    break

    def combine_nodes(self, node1: Node, node2: Node, combine_func) -> None:
        node1.content = combine_func(node1.content, node2.content)
        new_edge_set = set()
        for from_node, to_node in self.edge_set:
            if node2 == from_node:
                from_node = node1
            if node2 == to_node:
                to_node = node1
            new_edge_set.add((from_node, to_node))
        self.edge_set = new_edge_set
        self.nodes.remove(node2)

    def get_neighbors(self, node: Node) -> Set[Node]:
        neighbors = set()
        for from_node, to_node in self.edge_set:
            if node == from_node:
                neighbors.add(to_node)
            if node == to_node:
                neighbors.add(from_node)
        return neighbors

    def print(self, print_func=None):
        if not print_func:
            print_func = repr
        graph_name = "test"
        val = ["digraph {} {{".format(graph_name)]
        for node in self.nodes:
            val.append("    {} [label=\"{}\"];".format(id(node), print_func(node)))
        for from_node, to_node in self.edge_set:
            val.append("    {} -> {};".format(id(from_node), id(to_node)))
        val.append("}")
        print("\n".join(val))


def get_landmarks(start: Iterable[Term], goals: Iterable[Term], actions: Iterable[Action]):
    # is the goal currently met?
    # if not then find the differences

    action_list = [x for x in actions]

    freshness = {action: get_fresh(action) for action in action_list}

    graph = DiGraph()
    target_nodes = []
    for action, fresh in freshness.items():
        action_node = Node(action)
        graph.add_node(action_node)
        # group fresh by item name
        grouped_fresh = defaultdict(list)
        var_types = {}
        for add in fresh:
            if isinstance(add, Term) and len(add.literals) == 1:
                var_types[add.literals[0]] = add.predicate
            elif isinstance(add, Term) and len(add.literals) != 1:
                grouped_fresh[add.literals[0]].append(add)

        for var, group_list in grouped_fresh.items():
            for stmt in group_list:
                var_type = None
                try:
                    var_type = var_types[var]
                except KeyError:
                    for item in action.requirements:
                        if isinstance(item, Term) and len(item.literals) == 1 and item.literals[0] == var:
                            var_type = item.predicate
                assert var_type
                node = Node((var_type, stmt))
                graph.add_node(node)
                target_nodes.append(node)
                graph.add_edge(action_node, node)

    graph.unify_nodes(combine_terms)
    graph.compress_nodes(target_nodes, combine_terms)
    graph.print(node_print_function)


def node_print_function(node):
    if isinstance(node.content, Action):
        return node.content.name
    elif isinstance(node.content, tuple):
        return ': '.join([str(x) for x in node.content])
    elif isinstance(node.content, defaultdict):
        r = []
        for key in node.content:
            for set_item in node.content[key]:
                r.append(key + ": " + str(set_item))
        return "\\n".join(r)


def combine_terms(t1, t2):
    s = defaultdict(set)
    if isinstance(t1, tuple):
        for item in t1[1:]:
            s[t1[0]].add(item)
    elif isinstance(t1, defaultdict):
        s = t1
    else:
        raise CaseException

    if isinstance(t2, tuple):
        for item in t2[1:]:
            s[t2[0]].add(item)
    elif isinstance(t2, defaultdict):
        for key, set_of_terms in t2.items():
            s[key] |= set_of_terms
    else:
        raise CaseException

    return s


def old_get_landmarks(start: Iterable[Term], goals: Iterable[Term], actions: Iterable[Action]):
    action_list = [x for x in actions]

    action_match = []
    for action in action_list:
        unifiable_goals = unifiable(goals)
        for adds in itertools.combinations(action.add, len(goals)):
            unifiable_adds = unifiable(list(adds))
            if unify(unifiable_goals, unifiable_adds):
                # does it also unify with preconditions:
                found_match = False
                for pres in itertools.combinations(action.requirements, len(goals)):
                    if unify(unifiable_goals, unifiable(list(pres))):
                        found_match = True
                        break

                if not found_match:
                    action_match.append(action)

                break

    graph = []
    for goal in goals:
        # find all actions that directly have the goal as a postcondition
        for action in actions:
            for add_rule in action.add:
                if terms_equal(add_rule, goal):
                    action_match.append(action)
                    break

        # see if they are already in the graph
        pass

        # add them to the graph
        graph.append(action_match)

        # find any precondition that all goals share
        landmarks = set_intersect([set([CustomTerm(y) for y in x.requirements]) for x in action_match])

        # see if they are already in the graph
        pass

        # add to the graph
        graph.append(landmarks)
    return graph


class CustomTerm(object):
    def __init__(self, term):
        self.term = term

    def __eq__(self, other):
        return terms_equal(self.term, other.term)

    def __ne__(self, other):
        return not self.__eq__(self, other)

    def __hash__(self):
        return hash("{} {}".format(self.term.predicate, ['__VAR__' if isinstance(x, Variable) else '{}{}'.format(type(x),x) for x in self.term.literals]))


def terms_equal(t1: Term, t2: Term):
    # sees if two terms match
    if t1.predicate != t2.predicate:
        return False
    if len(t1.literals) != len(t2.literals):
        return False
    for l1, l2 in zip(t1.literals, t2.literals):
        if not (isinstance(l1, Variable) and isinstance(l2, Variable)):
            if l1 != l2:
                return False

    return True


def set_intersect(sets: List[Set]):
    # do an intersection on the sets using the comparison function
    intersect = sets.pop()
    for set in sets:
        intersect |= set

    return intersect
