from app.objects.secondclass.c_link import Link
from app.service.interfaces.i_planning_svc import PlanningServiceInterface
from app.utility.base_planning_svc import BasePlanningService


class PlanningService(PlanningServiceInterface, BasePlanningService):

    def __init__(self):
        super().__init__()
        self.log = self.add_service('planning_svc', self)

    async def exhaust_bucket(self, planner, bucket, operation, agent=None, batch=False, condition_stop=True):
        """Apply all links for specified bucket

        Blocks until all links are completed, either after batch push,
        or separately for every pushed link.

        :param planner: Planner to check for stopping conditions on
        :type planner: LogicalPlanner
        :param bucket: Bucket to pull abilities from
        :type bucket: string
        :param operation: Operation to run links on
        :type operation: Operation
        :param agent: Agent to run links on, defaults to None
        :type agent: Agent, optional
        :param batch: Push all bucket links immediately. Will check if
            operation has been stopped(by user) after all bucket links
            complete. 'False' will push links one at a time, and wait
            for each to complete. Will check if operation has been
            stopped (by user) after each single link is completed.
            Defaults to False
        :type batch: bool, optional
        :param condition_stop: Enable stopping of execution if stopping
            conditions are met. If set to False, the bucket will
            continue execution even if stopping conditions are met.
            defaults to True
        :type condition_stop: bool, optional
        """
        l_ids = []
        while True:
            links = await self.get_links(operation, [bucket], agent)
            if len(links) == 0:
                break
            for l in links:
                l_id = await operation.apply(l)
                if batch:
                    l_ids.append(l_id)
                else:
                    if await self.execute_links(planner, operation, [l_id], condition_stop):
                        return
            if batch:
                if await self.execute_links(planner, operation, l_ids, condition_stop):
                    return

    async def execute_links(self, planner, operation, link_ids, condition_stop):
        """Apply links to operation and wait for completion

        Optionally, stop bucket execution if stopping conditions are met

        :param planner: Planner to check for stopping conditions on
        :type planner: LogicalPlanner
        :param operation: Operation running links
        :type operation: Operation
        :param link_ids: Links IDS to wait for
        :type link_ids: list(string)
        :param condition_stop: Check and respect stopping conditions
        :type condition_stop: bool, optional
        :return: True if planner stopping conditions are met
        :rtype: bool
        """
        await self._bucket_execute(operation, planner, link_ids)
        return await self._stop_bucket_exhaustion(planner, operation, condition_stop)

    async def default_next_bucket(self, current_bucket, state_machine):
        """Returns next bucket in the state machine

        Determine and return the next bucket as specified in the given
        bucket state machine. If the current bucket is the last in the
        list, the bucket order loops from last bucket to first.

        :param current_bucket: Current bucket execution is on
        :type current_bucket: string
        :param state_machine: A list containing bucket strings
        :type state_machine: list
        :return: Bucket name to execute
        :rtype: string
        """
        idx = (state_machine.index(current_bucket) + 1) % len(state_machine)
        return state_machine[idx]

    async def add_ability_to_bucket(self, ability, bucket):
        """Adds bucket tag to ability

        :param ability: Ability to add bucket to
        :type ability: Ability
        :param bucket: Bucket to add to ability
        :type bucket: string
        """
        await ability.add_bucket(bucket)

    async def execute_planner(self, planner):
        """Default planner execution flow.

        This method will run the planner, progressing from bucket to
        bucket.

        Will stop execution for these conditions:
            - All buckets have been executed.
            - Planner stopping conditions have been met.
            - Operation was halted from external/UI input.

        NOTE: Do NOT call wait-for-link-completion functions here. Let
        the planner decide to do that within its bucket functions,
        and/or there are other planning_svc utilities for the bucket
        functions to use to do so.

        :param planner: Planner to run
        :type planner: LogicalPlanner
        """
        while planner.next_bucket is not None and not (planner.stopping_condition_met and planner.stopping_conditions) \
                and not await planner.operation.is_finished():
            await getattr(planner, planner.next_bucket)()
            await self.update_stopping_condition_met(planner, planner.operation)

    async def get_links(self, operation, buckets=None, agent=None, trim=True):
        """Generate links for use in an operation

        For an operation and agent combination, create links (that can
        be executed). When no agent is supplied, links for all agents
        are returned.

        :param operation: Operation to generate links for
        :type operation: Operation
        :param buckets: Buckets containing abilities. If 'None', get all links
            for given operation, agent, and trim setting. If a list of buckets
            if provided, then get links for specified buckets for given
            operation and trim setting. Defaults to None.
        :type buckets: list(string), optional
        :param agent: Agent to generate links for, defaults to None
        :type agent: Agent, optional
        :param trim: call trim_links() on list of links before
            returning, defaults to True
        :type trim: bool, optional
        :return: a list of links sorted by score and atomic ordering
        """
        ao = operation.adversary.atomic_ordering
        abilities = await self.get_service('data_svc') \
                              .locate('abilities', match=dict(ability_id=tuple(ao)))
        if buckets:
            # buckets specified - get all links for given buckets,
            # (still in underlying atomic adversary order)
            t = []
            for bucket in buckets:
                t.extend([ab for ab in abilities for b in ab.buckets if b == bucket])
            abilities = t
        links = []
        if agent:
            links.extend(await self.generate_and_trim_links(agent, operation, abilities, trim))
        else:
            for agent in operation.agents:
                links.extend(await self.generate_and_trim_links(agent, operation, abilities, trim))
        self.log.debug('Generated %s usable links' % (len(links)))
        return await self.sort_links(links)

    async def get_cleanup_links(self, operation, agent=None):
        """Generate cleanup links

        Generates cleanup links for given operation and agent. If no
        agent is provided, cleanup links will be generated for all
        agents in an operation.

        :param operation: Operation to generate links on
        :type operation: Operation
        :param agent: Agent to generate links on, defaults to None
        :type agent: Agent, optional
        :return: a list of links
        """
        links = []
        if agent:
            links.extend(await self._check_and_generate_cleanup_links(agent, operation))
        else:
            for agent in operation.agents:
                links.extend(await self._check_and_generate_cleanup_links(agent, operation))
        return reversed(links)

    async def generate_and_trim_links(self, agent, operation, abilities, trim=True):
        """Generate new links based on abilities

        Creates new links based on given operation, agent, and
        abilities. Optionally, trim links using `trim_links()` to return
        only valid links with completed facts.

        :param operation: Operation to generate links on
        :type operation: Operation
        :param agent: Agent to generate links on
        :type agent: Agent
        :param abilities: Abilities to generate links for
        :type abilities: list(Ability)
        :param trim: call trim_links() on list of links before
            returning, defaults to True
        :type trim: bool, optional
        :return: A list of links
        :rtype: list(Links)
        """
        agent_links = []
        if agent.trusted:
            agent_links = await self._generate_new_links(operation, agent, abilities, operation.link_status())
            await self._apply_adjustments(operation, agent_links)
            if trim:
                agent_links = await self.trim_links(operation, agent_links, agent)
        return agent_links

    async def check_stopping_conditions(self, stopping_conditions, operation):
        """Check operation facts against stopping conditions

        Checks whether an operation has collected the at least one of
        the facts required to stop the planner. Operation facts are
        checked against the list of facts provided by the stopping
        conditions. Facts will be validated based on the `unique`
        property, which is a combination of the fact trait and value.

        :param stopping_conditions: List of facts which, if collected,
            should be used to terminate the planner
        :type stopping_conditions: list(Fact)
        :param operation: Operation to check facts on
        :type operation: Operation
        :return: True if all stopping conditions have been met, False
            if all stopping conditions have not been met
        :rtype: bool
        """
        for sc in stopping_conditions:
            if not await self._stopping_condition_met(operation.all_facts(), sc):
                return False
        return True

    async def update_stopping_condition_met(self, planner, operation):
        """Update planner `stopping_condition_met` property

        :param planner: Planner to check stopping conditions and update
        :type planner: LogicalPlanner
        :param operation: Operation to check facts on
        :type operation: Operation
        """
        if planner.stopping_conditions:
            planner.stopping_condition_met = await self.check_stopping_conditions(planner.stopping_conditions,
                                                                                  operation)

    @staticmethod
    async def sort_links(links):
        """Sort links by score and atomic ordering in adversary profile

        :param links: List of links to sort
        :type links: list(Link)
        :return: Sorted links
        :rtype: list(Link)
        """
        return sorted(links, key=lambda k: (-k.score))

    """ PRIVATE """

    async def _bucket_execute(self, operation, planner, links):
        """Wait for operation links to complete and update planner

        Blocks execution until all links from the operation are
        completed. Once links are completed, update the planner's
        `stopping_condition_met` property.

        :param operation: Operation to wait for links on
        :type operation: Operation
        :param planner: Planner to check stopping conditions and update
        :type planner: LogicalPlanner
        :param links: Links IDs to wait for
        :type links: list(string)
        """
        await operation.wait_for_links_completion(links)
        await self.update_stopping_condition_met(planner, operation)

    async def _stop_bucket_exhaustion(self, planner, operation, condition_stop):
        """Determine whether to continue running the bucket or not

        Check if the operation is finished. If `condition_stop` is True,
        also check that at least one of the planner's stopping
        conditions has been met.

        :param planner: Planner to check stopping conditions and update
        :type planner: LogicalPlanner
        :param operation: Operation to wait for links on
        :type operation: Operation
        :param condition_stop: Check and respect stopping conditions
        :type condition_stop: bool
        :return: True if the operation is finished and the stopping
            conditions are met
        :rtype: bool
        """
        if await operation.is_finished() or (condition_stop and planner.stopping_condition_met):
            return True
        return False

    @staticmethod
    async def _stopping_condition_met(facts, stopping_condition):
        """Check if given stopping condition is in the list of facts

        :param facts: List of facts to compare to the stopping condition
        :type facts: list(Fact)
        :param stopping_condition: Single fact to search for in facts
        :type stopping_condition: Fact
        :return: True if the stopping condition is in the facts list
        :rtype: bool
        """
        for f in facts:
            if f.unique == stopping_condition.unique:
                return True
        return False

    async def _check_and_generate_cleanup_links(self, agent, operation):
        """Generate cleanup links if agent is trusted

        Links will be generated with a status based on the operation
        link status.

        :param agent: Agent to generate cleanup links for
        :type agent: Agent
        :param operation: Operation to generate cleanup links for
        :type operation: Operation
        :return: Cleanup links for agent
        :rtype: list(Link)
        """
        agent_cleanup_links = []
        if agent.trusted:
            agent_cleanup_links = await self._generate_cleanup_links(operation=operation,
                                                                     agent=agent,
                                                                     link_status=operation.link_status())
        return agent_cleanup_links

    async def _generate_new_links(self, operation, agent, abilities, link_status):
        """Generate links with given status

        :param operation: Operation to generate links on
        :type operation: Operation
        :param agent: Agent to generate links on
        :type agent: Agent
        :param agent: Abilities to generate links for
        :type agent: list(Ability)
        :param link_status: Link status, referencing link state dict
        :type link_status: int
        :return: Links for agent
        :rtype: list(Link)
        """
        links = []
        for a in await agent.capabilities(abilities):
            if a.code and a.HOOKS:
                await a.HOOKS[a.language](a)
            if a.test:
                links.append(
                    Link.load(dict(command=a.test, paw=agent.paw, score=0, ability=a,
                                   status=link_status, jitter=self.jitter(operation.jitter)))
                )
        return links

    async def _generate_cleanup_links(self, operation, agent, link_status):
        """Generate cleanup links with given status

        :param operation: Operation to generate cleanup links for
        :type operation: Operation
        :param agent: Agent to generate cleanup links for
        :type agent: Agent
        :param link_status: Link status, referencing link state dict
        :type link_status: int
        :return: Cleanup links for agent
        :rtype: list(Link)
        """
        links = []
        for link in [l for l in operation.chain if l.paw == agent.paw]:
            ability = (await self.get_service('data_svc').locate('abilities',
                                                                 match=dict(unique=link.ability.unique)))[0]
            for cleanup in ability.cleanup:
                decoded_cmd = agent.replace(cleanup, file_svc=self.get_service('file_svc'))
                variant, _, _ = await self._build_single_test_variant(decoded_cmd, link.used, link.ability.executor)
                lnk = Link.load(dict(command=self.encode_string(variant), paw=agent.paw, cleanup=1,
                                     ability=ability, score=0, jitter=2, status=link_status))
                if lnk.command not in [l.command for l in links]:
                    lnk.apply_id(agent.host)
                    links.append(lnk)
        return links

    @staticmethod
    async def _apply_adjustments(operation, links):
        """Apply operation source ability adjustments to links

        :param operation: Operation to use for source adjustments
        :type operation: Operation
        :param links: Links to apply adjustments to
        :type links: list(Link)
        """
        for l in links:
            for adjustment in [a for a in operation.source.adjustments if a.ability_id == l.ability.ability_id]:
                if operation.has_fact(trait=adjustment.trait, value=adjustment.value):
                    l.visibility.apply(adjustment)
                    l.status = l.states['HIGH_VIZ']
