import typing
from typing import List, Tuple, Union, Set, Dict
import time
import functools
import logging
from enum import Enum
from collections import defaultdict

from .logic import Variable, Comparison, Term, LogicContext, convert_to_action, Action, Unary
from ..util import CaseException

log = logging.getLogger(__name__)


class Meaning(Enum):
    Primary = 1
    Secondary = 2
    NotMeaningful = 3


class QuickList(object):
    """List with O(1) lookup"""

    def __init__(self):
        self.l = list()
        self.s = set()

    def pop(self):
        self.l.pop()
        self.s = set(self.l)

    def __contains__(self, item):
        return item in self.s

    def push(self, item):
        self.l.append(item)
        self.s.add(item)


class LogicFrame(object):
    counter = 0

    def __init__(self, logic):
        self.frames = []
        self.logic = logic

    def push(self, frame):
        self.frames.append(frame)
        for positivity, term in frame:
            if positivity == "assert":
                self.logic.assert_fact(term)
            elif positivity == "retract":
                self.logic.retract_fact(term)
            else:
                raise Exception("invalid positivity: {}".format(positivity))

    def pop(self):
        """Removes the top-most frame from the stack, and un-defines all the facts that were defined in that frame
        """
        popped = self.frames.pop()

        # inverse the popped objects
        for positivity, term in reversed(popped):
            if positivity == "assert":
                self.logic.retract_fact(term)
            elif positivity == "retract":
                self.logic.assert_fact(term)
            else:
                raise Exception("invalid positivity: {}".format(positivity))


# Some descriptions:
#       has_member(X, Y, fZ)
#           --> Z is a member of Y, which belongs to X
#           --> Z \in X.Y
#       has_property(X, Y, Z)
#           --> X has property Y equal to Z
#           --> Z = X.Y
class PlannerContext(object):
    counter = 0

    """This is the planner. It takes a list of actions and calculates the 'best' next action."""

    def __init__(self, logic: LogicContext, rec_limit, performed_actions=None):
        self.logic = logic
        self.action_frames = LogicFrame(self.logic)
        self.actions = {}
        self.uncommitted_actions = QuickList()
        self.uncommitted_significants = QuickList()
        self.banned_actions = QuickList()
        if performed_actions is not None:
            self.committed_actions = performed_actions
            # convert these to significants as actions are added
            self.committed_significants = list(performed_actions)
        else:
            self.committed_actions = []
            self.committed_significants = []
        self.counter = 0
        self.rec_limit = rec_limit
        self.recs = {}
        self.is_primary_typ = {}

        self.logic.define_predicate('has_property', 3)
        self.logic.define_predicate('has_member', 3)

    @classmethod
    def unique_count(cls) -> int:
        """A unique counter

        Returns:
            A unique number
        """
        cls.counter += 1
        return cls.counter

    def print_dump(self):
        """Prints all the facts in the database.
        """
        for item in self.get_dump():
            print(str(item))

    def get_dump(self):
        """
        Returns all the facts in the database
        Returns:
            The list of database facts.
        """
        return sorted(self.logic.get_facts())

    def assert_fact(self, fact: Term):
        """Adds a logical fact to the planner's knowledgebase

        Args:
            fact: the term representing the fact
        """
        self.logic.assert_fact(fact)

    def retract_fact(self, fact: Term):
        """Removes a logical fact from the planner's knowledgebase

        Args:
            fact: the term representing the fact
        """
        self.logic.retract_fact(fact)

    def bind_variables(self, facts: typing.List[typing.Tuple[str, Term]]):
        bindings = {}
        facts = sorted(facts, key=lambda x: len(x[1].literals))

        bound_facts = []

        for positivity, term in facts:
            # Check to see if anything in this term is already bound
            term.literals = [x if x not in bindings else bindings[x] for x in term.literals]
            if term.predicate in self.is_primary_typ:
                assert len(term.literals) == 1
                if isinstance(term.literals[0], Variable):
                    # we have something like "ophost(VARIABLE)"
                    preamble = term.predicate[2:]
                    bindings[term.literals[0]] = preamble + str(self.unique_count())
                    term.literals[0] = bindings[term.literals[0]]
                bound_facts.append((positivity, term))
            elif term.predicate in ("has_property", "has_member"):
                assert term.count_variables() == 0
                bound_facts.append((positivity, term))
            elif term.predicate == "defines_property":
                assert len(term.literals) == 2
                new_term = Term("has_property", term.literals[0], term.literals[1],
                                term.literals[1] + str(self.unique_count()))

                bound_facts.append((positivity, new_term))
            else:
                raise Exception("Not found: {}".format(term.predicate))
        return bound_facts

    def action_meaning(self, action: Action, *action_args) -> Meaning:
        """Tells if the action is meaningful in the given context

        Args:
            action: The action
            *action_args: The action's arguments

        Returns:
            True if the action is meaningful, else False
        """
        if not action.deterministic:
            # random actions are meaningful only if their significant parameters are unique
            significant_args = [x for i, x in enumerate(action_args) if i in action.significant_parameters]
            return Meaning.Primary if (action.name, *significant_args) not in self.uncommitted_significants and \
                                      (action.name,
                                       *significant_args) not in self.committed_significants else Meaning.NotMeaningful

        elif action.name == "NetUse" or action.name == "net_use":
            return Meaning.Secondary
        else:
            return Meaning.Primary
            retval = Meaning.NotMeaningful
            # deterministic actions are only meaningful if their postconditions do not already exist
            postconds = action.build_post_conditions(*action_args)
            object_types = {}
            type_collection = defaultdict(list)
            for positivity, postcond in postconds:
                if isinstance(postcond, Term) and postcond.predicate not in ('has_property', 'has_member',
                                                                             'defines_property'):
                    object_types[postcond.literals[0]] = postcond.predicate
                elif isinstance(postcond, Term) and postcond.predicate in ('has_property', 'has_member'):
                    if isinstance(postcond.literals[0], Variable):
                        type_collection[postcond.literals[0]].append((positivity, postcond))
                    else:
                        raise CaseException

            # group all postconds by object
            for key, collected in type_collection.items():
                variable = Variable('T')

                termed = []
                for positivity, postcond in collected:
                    t = Term(postcond.predicate)
                    t.literals = [variable, *postcond.literals[1:]]
                    termed.append(t)

                object_type = object_types[key]
                expression = Term(object_type)
                expression.literals = [variable]
                while termed:
                    t = termed.pop()
                    expression = Comparison('&', expression, t)

                query_result = self.logic.query(expression)
                # if a postcondition does not exist yet, this action is meaningful
                if not query_result:
                    if self.is_primary_typ[object_type]:
                        return Meaning.Primary
                    else:
                        retval = Meaning.Secondary

            return retval

    def add_step(self, step):
        """Adds a step to the planner, creating an action object to represent it.

        Args:
            step: the step to be added

        Returns:
            The action that was created for the step
        """
        action = convert_to_action(step, self.unique_count)
        self.add_action(action)
        return action

    def add_action(self, action: Action):
        """Adds an action to the planner

        Args:
            action: the action to be added
        """
        self.actions[action.name] = action

        if action.deterministic:
            meaning_rules = action.get_meaningful_rules()
            rule = action.get_rule()
            meaning_disjunction = None
            for meaning_rule in meaning_rules:
                self.logic.define_rule(meaning_rule)
                if meaning_disjunction:
                    meaning_disjunction = Comparison('|', meaning_disjunction,
                                                     Unary('~', Term(meaning_rule.name, *meaning_rule.parameters)))
                else:
                    meaning_disjunction = Unary('~', Term(meaning_rule.name, *meaning_rule.parameters))
            rule.body = Comparison('&', rule.body, meaning_disjunction)
        else:
            rule = action.get_rule()

        self.logic.define_rule(rule)

        # rebuild the committed_significants now that we know the action
        def get_sig_args(l):
            return (action.name, *[a for i, a in enumerate(l) if i in action.significant_parameters])

        self.committed_significants = [(action_name, *args) if action_name != action.name else get_sig_args(args) for
                                       action_name, *args in self.committed_significants]

    def do_action(self, action: Action, *parameters):
        """Logically performs the action by adding its post-conditions to the planners knowledge

         Args:
            action: the action to be added
            *parameters: the action's parameters
        """
        facts = self.bind_variables(action.build_post_conditions(*parameters))
        facts = sorted(facts, key=lambda x: len(x[1].literals))
        self.action_frames.push(facts)

        self.do_action_without_postconditions(action, *parameters, success=True)

    def do_action_without_postconditions(self, action: Action, *action_args, success, commit=False):
        """Performs an action by adding it to the list of actions that have been performed, without adding its
        post-conditions to the knowledge-base

        Args:
            action: the action
            *action_args: the action's arguments
            commit: if true, commits the action by adding this to the planners committed_actions and
                    committed_significants variables, otherwise uses the uncommitted version of these variables
        """
        sig_args = [x for i, x in enumerate(action_args) if i in action.significant_parameters]
        if success:
            if commit:
                self.committed_actions.append((action.name, *action_args))
                self.committed_significants.append((action.name, *sig_args))
            else:
                self.uncommitted_actions.push((action.name, *action_args))
                self.uncommitted_significants.push((action.name, *sig_args))
        else:
            # Step Failed
            if (action.name, action_args) in self.recs:
                self.recs[(action.name, action_args)] += 1
            else:
                self.recs[(action.name, action_args)] = 1
            if self.recs[(action.name, action_args)] >= self.rec_limit:
                self.do_ban_action(action, *action_args)

    def undo_action(self):
        """Undoes the most recent action. by popping the topmost fact frame, and removed in from the uncommitted* lists.
        """
        self.action_frames.pop()
        self.uncommitted_actions.pop()
        self.uncommitted_significants.pop()

    def do_ban_action(self, action: Action, *action_args):
        self.banned_actions.push((action.name, *action_args))

    def done_action(self, action: Action, *action_args) -> bool:
        """Returns true if the action has been performed already

        Args:
            action: the action
            *action_args: it's arguments
        """
        return (action.name, *action_args) in self.uncommitted_actions or \
               (action.name, *action_args) in self.committed_actions

    def banned_action(self, action: Action, *action_args) -> bool:
        """ Returns true if the action has been invalidated (recursion limit reached)
        Args:
            action: the action
            *action_args: it's arguments
        """
        return (action.name, *action_args) in self.banned_actions

    def get_all_action_instances(self, action: Action):
        """Gets all of the possible action arguments for this action

        Args:
            action: the action

        Returns:
            A list of tuples, where each tuple is one set of valid arguments to the action
        """
        return self.logic.query(Term(action.name, *action.parameters))

    def plan(self, time_limit: Union[int, None], max_depth: int, max_returns: int = 500000) -> List:
        """Generates plans.

        Args:
            time_limit: the maximum amount of time to spend planning or None for infinite time
            max_depth: the depth to plan to
            max_returns: the maximum numbers of plans to return

        Returns:
            A list of plans
        """
        # from line_profiler import LineProfiler
        # lp = LineProfiler()
        # lp_wrapper = lp(self._recursive_planner)
        # num_plans, plans = lp_wrapper(time_limit, max_depth, max_depth, defaultdict(set))
        # lp.dump_stats("stats.out")
        num_plans, plans = self._recursive_planner(time_limit, max_depth, max_depth, defaultdict(set))

        log.debug("Processed " + str(num_plans) + " plans")
        # Return the top <max_return> plans within each group
        # Sort each array using the eval_plan function (partial!!)
        plans.sort(key=lambda x: -eval_plan(x))
        return plans[:max_returns]

    def _recursive_planner(self, time_limit: Union[int, None], total_depth: int, current_depth: int,
                           ignore_actions: Dict[Action, Set]) -> Tuple[int, List]:
        """Recursively generates plans

        Args:
            time_limit: the maximum amount of time to spend planning or None for infinite time
            total_depth: how deep to plan
            current_depth: the current planning depth
            ignore_action: the set of action_args which should not be followed

        Returns:
            The plans
        """
        start_time = time.process_time()
        explored_actions = 0
        identified_plans = []
        # if current_depth is 0, just return empty
        if current_depth == 0:
            return explored_actions, identified_plans

        # otherwise, get all the actions we can do
        all_action_args = {}
        for action in self.actions.values():
            all_instances = self.get_all_action_instances(action)
            all_instances -= ignore_actions[action]
            all_action_args[action] = all_instances

        for action, all_args in all_action_args.items():
            ignore_actions[action] |= all_args

        meaningful_action_args = set()
        for action in all_action_args:
            for t in all_action_args[action]:
                if not self.done_action(action, *t) and \
                        not self.banned_action(action, *t) and \
                                self.action_meaning(action, *t) != Meaning.NotMeaningful:
                    meaningful_action_args.add((action, t))

        t1 = time.process_time()

        # remove actions that are basically duplicates of each other
        def strip(action, args):
            all_tuples = []
            for index in range(0, len(args)):
                if index in action.non_params:
                    all_tuples.append(tup[index])
            return tuple(all_tuples)

        action_map = {}
        for action, tup in meaningful_action_args:
            stripped_tuple = strip(action, tup)
            action_map[(action, stripped_tuple)] = (action, tup)

        deduped_action_args = set()
        for value in action_map.values():
            deduped_action_args.add(value)

        t2 = time.process_time()

        # get all the actions + argument tuples stored by their action
        action_args_by_action = defaultdict(list)
        for action, t in deduped_action_args:
            action_args_by_action[action].append((action, t))

        # if there aren't any plans at this point, return
        if not action_args_by_action:
            # remove any ignored args
            for action, all_args in all_action_args.items():
                ignore_actions[action] -= all_args
            return explored_actions, identified_plans

        # look for actions that are mathematically impossible to beat
        max_score = max(map(lambda x: x.score, self.actions.values()))
        high_score = 0
        optimal_action_args_by_action = defaultdict(list)
        for action in sorted(self.actions.values(), key=lambda x: -x.score):
            if action.score > max_score / 2 and action.score >= high_score and action_args_by_action[action]:
                optimal_action_args_by_action[action] = action_args_by_action[action]

        # if there are optimal solutions, use them instead
        if len(optimal_action_args_by_action):
            log.debug("found {} mathematically optimal actions".format(len(optimal_action_args_by_action)))
            action_args_by_action = optimal_action_args_by_action

        t3 = time.process_time()

        log.debug(
            "After pruning, {} actions left to evaluate".format(sum(map(len, list(action_args_by_action.values())))))
        # evaluate the possible actions we have left by simulating them
        for action, t in roundrobin(*action_args_by_action.values()):
            meaning = self.action_meaning(action, *t)
            if identified_plans and time_limit and time.process_time() - start_time >= time_limit:
                log.debug("Planning time limit reached, returning {} plan(s)".format(len(identified_plans)))
                break

            explored_actions += 1
            new_entry = (action.name, t, action.score)

            new_plans = []
            if current_depth > 1:
                self.do_action(action, *t)
                new_explored, new_plans = self._recursive_planner(None, total_depth, current_depth - 1, ignore_actions)
                explored_actions += new_explored
                self.undo_action()
            elif current_depth == 1 and total_depth == 1 and meaning == Meaning.Secondary:
                # add an extra planning step here to give leaf secondary nodes a chance to be meaningful
                self.do_action(action, *t)
                new_explored, new_plans = self._recursive_planner(None, 2, 1, ignore_actions)
                explored_actions += new_explored
                self.undo_action()
            if len(new_plans) == 0:
                if meaning != Meaning.Secondary:
                    # secondary actions are not important if they are leafs
                    identified_plans.append([new_entry])
            else:
                if meaning != Meaning.Secondary:
                    for plan in new_plans:
                        identified_plans.append([new_entry] + plan)
                else:
                    # secondary actions are only important if they lead to an action that wasn't possible before
                    for plan in new_plans:
                        for plan_action_name, plan_action_args, score in plan:
                            if (self.actions[plan_action_name], plan_action_args) not in all_action_args:
                                identified_plans.append([new_entry] + plan)
                                break

        t4 = time.process_time()

        if total_depth == current_depth:
            log.warning("Planning run took {} seconds and returned {} actions".format(t1 - start_time, sum(
                (len(x) for x in all_action_args.values()), 0)))
            log.warning(
                "Dedupping took {} seconds and returned {} actions".format(t2 - t1, len(meaningful_action_args)))
            log.warning("Optimization pruning took {} seconds and returned {} actions".format(t3 - t2, len(
                optimal_action_args_by_action)))
            log.warning("Recursion took {} seconds and explored {} actions".format(t4 - t3, explored_actions))
            log.warning("Action Breakdown:")
            for action in sorted(action_args_by_action, key=lambda x: -len(action_args_by_action[x])):
                log.warning("    {}: {}".format(len(action_args_by_action[action]), action.name))

        # remove any ignored args
        for action, all_args in all_action_args.items():
            ignore_actions[action] -= all_args
        return explored_actions, identified_plans

    def define_type(self, typ: str, primary=True):
        """Defines a type.

        Args:
            typ: The type
            primary: True if this is a primary type. Primary types are interpreted as important objects, so the planner
                     will interpret actions that produce new primary type objects as useful. Objects that aren't useful
                     in and of themselves (for example network shares) should not be treated as primary types.
        """
        self.is_primary_typ[typ.lower()] = primary
        self.logic.define_predicate(typ.lower(), 1)

    def define_object(self, typ: str, name, obj: dict):
        """Defines an object in the knowledge-base of the planner.

        Args:
            typ: the type of the object
            name: a hashable object that uniquely identifies this object
            obj: a dict of fields represented the properties of this object
        """
        typ = typ.lower()
        assert typ in self.is_primary_typ
        if not isinstance(name, str):
            name = str(name)
        self.assert_fact(Term(typ, name))
        for key, value in obj.items():
            if isinstance(value, list):
                for item in value:
                    if not isinstance(value, str) and not isinstance(value, bool) and not isinstance(value, int):
                        item = str(item)
                    self.assert_fact(Term('has_member', name, key, item))
            else:
                if not isinstance(value, str) and not isinstance(value, bool) and not isinstance(value, int):
                    value = str(value)
                self.assert_fact(Term('has_property', name, key, value))

    def undefine_all_objects(self):
        """Removes all defined objects.
        """
        self.logic.retract_all_facts()

    def close(self):
        """Closes this planner instance by performing any necessary cleanup activities."""
        self.logic.close()

    def best_action(self, plan_length: int, time_limit: int):
        """Runs the planner and returns the best possible action.

        Args:
            plan_length: the plan length
            time_limit: the maximum amount of time to spend planning or None for infinite time

        Returns:
            The best possible action, a tuple of the actions arguments or None, None if no plans could be found
        """
        old_plans = self.plan(time_limit, plan_length)
        try:
            return self.actions[old_plans[0][0][0]], old_plans[0][0][1]
        except IndexError:
            return None, None

    def all_actions(self, plan_length):
        """Runs the planner and returns all possible actions.

        Args:
            plan_length: the length to plan to

        Returns:
            A list of (action, parameters) tuples representing all possible actions
        """
        old_plans = self.plan(5, plan_length)
        actions = [(a[0][0], a[0][1]) for a in old_plans]
        seen = set()
        seen_add = seen.add
        actions = [x for x in actions if not (x in seen or seen_add(x))]
        return actions

    # Throws IndexError if there are no more plans
    def perform_best_step(self, plan_length: int, time_limit: int):
        """Runs the planner, selecting the best possible step and return the arguments for that step

        Args:
            plan_length: the plan length
            time_limit: the amount of time to spend planning before being forced to return or None for infinite

        Returns:
            The step, arguments to the step, and a callback that should be called if the step was successfully run or
            None, None, None if there are no more plans
        """
        action, args = self.best_action(plan_length, time_limit)

        if action is None or args is None:
            return None, None, None
        args_by_name = {k: v for k, v in zip(action.parameters, args)}

        # convert the action and the parameters back to step
        # keys are the step names of parameters and value are the action names
        arguments = {step_arg: args_by_name[action.bindings[step_arg]] for step_arg, _ in action.step.preconditions}

        return action.step, arguments, functools.partial(self.do_action_without_postconditions, action, *args,
                                                         commit=True)


def roundrobin(*lists):
    idx = 0
    max_idx = max(map(len, lists))
    while idx < max_idx:
        for l in lists:
            try:
                yield l[idx]
            except IndexError:
                pass
        idx += 1


def eval_plan(plan):
    if plan is None:
        return 0
    counter = 1
    total = 0
    for t in plan:
        total += t[2] / counter
        counter += 1
    return total
