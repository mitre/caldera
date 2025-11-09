import asyncio
from typing import Dict, List
from dataclasses import dataclass
from collections import defaultdict

from app.objects.c_ability import Ability
from app.objects.c_operation import Operation
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_relationship import Relationship
from app.service.planning_svc import PlanningService


OP_APPLY_SLEEP_S          = 0.1
OP_WAIT_LINK_COMPLETION_S = 0.1


@dataclass
class Action:
    """
    Represents an Action from an actions.json file
    Basically a lighter version of a Link
    """
    agent_paw   : str
    ability_uuid: str
    facts       : Dict[str, str]


class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation              = operation
        self.planning_svc           = planning_svc
        self.stopping_conditions    = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine          = ['automation']
        self.next_bucket            = 'automation'

    async def execute(self):
        await self.planning_svc.execute_planner(self)

    async def op_apply(self, link: Link):
        """
        Modified version of Operation.apply() to allow increasing polling rate
        (only for RUN_ONE_LINK state though)
        """
        op = self.operation

        while op.state != op.states['RUNNING']:
            if op.state == op.states['RUN_ONE_LINK']:
                op.add_link(link)
                op.state = op.states['PAUSED']
                return link.id
            else:
                await asyncio.sleep(OP_APPLY_SLEEP_S)
        op.add_link(link)
        return link.id

    async def op_wait_for_link_completion(self, link_id):
        """
        Modified variant of Operation.wait_for_links_completion() to allow
        increasing polling rate by lowering sleep (and is only for a single Link)
        """
        op = self.operation

        link = [link for link in op.chain if link.id == link_id][0]
        if link.can_ignore():
            op.ignored_links.add(link.id)
        member = [member for member in op.agents if member.paw == link.paw][0]
        while not (link.finish or link.can_ignore()):
            await asyncio.sleep(OP_WAIT_LINK_COMPLETION_S)
            if not member.trusted:
                break

    async def create_action_list(self) -> List[Action]:
        """
        Creates a list of Actions by parsing the Action Fact Bundles from the
        Operation's Relationships (loaded from a Source)
        """
        op  : Operation          = self.operation
        rels: List[Relationship] = await op.all_relationships()

        action_dict: Dict[int, Action] = defaultdict(lambda: Action('', '', {}))

        for r in rels:
            source: Fact = r.source
            edge  : str  = r.edge
            target: Fact = r.target

            if source.trait != 'operation.action.index':
                continue

            action = action_dict[int(source.value)]

            if edge == 'agent':
                action.agent_paw = target.value
            elif edge == 'ability':
                action.ability_uuid = target.value
            elif edge == 'fact':
                action.facts[target.trait] = target.value

        action_list: List[Action] = [None] * len(action_dict)

        for index, action in action_dict.items():
            action_list[index] = action

        return action_list

    def check_action_link_eq(self, action: Action, link: Link) -> bool:
        """
        Tests (Action == Link)
        """
        link_ability: Ability    = link.ability
        link_infacts: List[Fact] = link.used

        if action.ability_uuid != link_ability.ability_id:
            return False

        if action.agent_paw != link.paw:
            return False

        for f in link_infacts:
            if action.facts.get(f.trait) != f.value:
                return False

        return True

    def create_link_lookup(self, links: List[Link]) -> Dict[str, Dict[str, List[Link]]]:
        """
        Creates a nested dict of lists for fast Link lookup
        lookup[agent_paw][ability_uuid] -> [list of potential links for this agent+ability combo]
        """
        paw_ability_to_link = defaultdict(lambda: defaultdict(list))

        for link in links:
            ability: Ability = link.ability
            paw_ability_to_link[link.paw][ability.ability_id].append(link)

        return paw_ability_to_link

    async def automation(self):
        """
        1. Parses Actions from the Fact Source
        2. Generates all possible Links (many can be invalid)
        3. Indexes these Links for fast lookup
        4. Loops through the Actions
           a. Finds the matching Link
           b. Executes it
        """
        plan_svc: PlanningService = self.planning_svc
        op      : Operation       = self.operation

        actions = await self.create_action_list()

        links: List[Link] = await plan_svc.get_links(operation=op)
        link_lookup       = self.create_link_lookup(links)

        for action in actions:
            matches = link_lookup[action.agent_paw][action.ability_uuid]

            ind, match = next((
                (ind, m)
                for ind, m in enumerate(matches)
                if self.check_action_link_eq(action, m)
            ), (None, None))

            if match is None:
                print('>>>> ERROR - LIMITATION: Cannot Run Non-Repeatable Ability More Than Once Per Agent <<<<')
                break

            del matches[ind]

            link_id = await self.op_apply(match)
            await self.op_wait_for_link_completion(link_id)

        self.next_bucket = None
