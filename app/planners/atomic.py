class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['atomic']
        self.next_bucket = 'atomic'   # repeat this bucket until we run out of links.

    async def execute(self):
        await self.planning_svc.execute_planner(self)

    async def atomic(self):
        links_to_use = []

        # Get the first available link for each agent (make sure we maintain the order).
        for agent in self.operation.agents:
            possible_agent_links = await self._get_links(agent=agent)
            next_link = await self._get_next_atomic_link(possible_agent_links)
            print(f'[Atomic] Next atomic link for agent {agent.paw} is {next_link}')
            if next_link:
                for link in possible_agent_links:
                    links_to_use.append(await self.operation.apply(link))

        if links_to_use:
            # Each agent will run the next available step.
            print(f'[Atomic] Running {len(links_to_use)} links with links_to_use: {links_to_use}')
            await self.operation.wait_for_links_completion(links_to_use)
        else:
            # No more links to run.
            self.next_bucket = None

    async def _get_links(self, agent=None):
        return await self.planning_svc.get_links(operation=self.operation, agent=agent)

    # Given list of links, returns the link that appears first in the adversary's atomic ordering.
    async def _get_next_atomic_link(self, possible_links):
        # 1. Try to match based on explicit step_idx
        link_lookup = {link.step_idx: link for link in possible_links if hasattr(link, 'step_idx')}

        for idx, _ in enumerate(self.operation.adversary.atomic_ordering):
            if idx in link_lookup:
                return link_lookup[idx]

        # 2. Fallback to ability_id matching (legacy style)
        abil_id_to_link = {link.ability.ability_id: link for link in possible_links}
        candidate_ids = set(abil_id_to_link.keys())

        for step in self.operation.adversary.atomic_ordering:
            ability_id = step if isinstance(step, str) else step.get('ability_id')
            if ability_id in candidate_ids:
                return abil_id_to_link[ability_id]

        return None

