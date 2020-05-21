from app.objects.secondclass.c_link import Link
from app.service.interfaces.i_planning_svc import PlanningServiceInterface
from app.utility.base_planning_svc import BasePlanningService


class PlanningService(PlanningServiceInterface, BasePlanningService):

    def __init__(self):
        super().__init__()
        self.log = self.add_service('planning_svc', self)

    async def exhaust_bucket(self, planner, bucket, operation, agent=None, batch=False, condition_stop=True):
        """
        Apply all links for specified bucket. Blocks until all links are completed,
        either after batch push, or seperately for every pushed link.

        :param planner:
        :param bucket:
        :param operation:
        :param agent:
        :param batch: (bool) 'True' - push all bucket links immediately. Will check
            if operation has been stopped(by user) after all bucket links complete.
            'False' will push links one at a time, and wait for each to
            complete. Will check if operation has been stopped(by user) after
            each single link is completed.
        :param condition_stop: (bool) check and respect stopping conditions
        :return:
        """
        l_ids = []
        for l in await self.get_links(operation, bucket, agent):
            l_id = await operation.apply(l)
            if batch:
                l_ids.append(l_id)
            else:
                await self._bucket_execute(operation, planner, [l_id], condition_stop)
                if await self._stop_bucket_exhaustion(planner, operation, condition_stop):
                    return
        if batch:
            await self._bucket_execute(operation, planner, l_ids, condition_stop)
            if await self._stop_bucket_exhaustion(planner, operation, condition_stop):
                return

    async def default_next_bucket(self, current_bucket, state_machine):
        """
        Returns next bucket as specified in planner's defined bucket
        state machine. Loops from last bucket to first.
        """
        idx = (state_machine.index(current_bucket) + 1) % len(state_machine)
        return state_machine[idx]

    async def add_ability_to_bucket(self, ability, bucket):
        """Adds bucket tag to ability"""
        await ability.add_bucket(bucket)

    async def execute_planner(self, planner):
        """
        Default planner execution flow. Progress from bucket to bucket. Will stop
        execution for these conditions:
            - All buckets have been executed.
            - Planner stopping conditions have been met.
            - Operation was halted from external/UI input.

        NOTE: Do NOT call wait-for-link-completion functions here. Let the planner
        decide to do that within its bucket functions, and/or there are other
        planning_svc utilities for the bucket functions to use to do so.
        """
        while planner.next_bucket is not None and not (planner.stopping_condition_met and planner.stopping_conditions) \
                and not await planner.operation.is_finished():
            await getattr(planner, planner.next_bucket)()
            await self.update_stopping_condition_met(planner, planner.operation)

    async def get_links(self, operation, buckets=None, agent=None, trim=True, planner=None):
        """
        For an operation and agent combination, create links (that can be executed).
        When no agent is supplied, links for all agents are returned

        :param operation:
        :param bucket:
            'None' - no buckets, get all links for given operation, agent, trim setting
            '<bucket>' - get links for specified bucket for given trim setting
        :param agent:
        :param trim: call trim_links() on list of links before returning
        :param planner:
        :return: a list of links
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
        links = []
        if agent:
            links.extend(await self._check_and_generate_cleanup_links(agent, operation))
        else:
            for agent in operation.agents:
                links.extend(await self._check_and_generate_cleanup_links(agent, operation))
        return reversed(links)

    async def generate_and_trim_links(self, agent, operation, abilities, trim=True):
        agent_links = []
        if agent.trusted:
            agent_links = await self._generate_new_links(operation, agent, abilities, operation.link_status())
            await self._apply_adjustments(operation, agent_links)
            if trim:
                agent_links = await self.trim_links(operation, agent_links, agent)
        return agent_links

    async def check_stopping_conditions(self, stopping_conditions, operation):
        """
        Checks whether an operation has collected the proper facts to trigger this planner's stopping
        conditions

        :return: True if all stopping conditions have been met, False if all stopping conditions have not
        been met
        """
        for sc in stopping_conditions:
            if not await self._stopping_condition_met(operation.all_facts(), sc):
                return False
        return True

    async def update_stopping_condition_met(self, planner, operation):
        if planner.stopping_conditions:
            planner.stopping_condition_met = await self.check_stopping_conditions(planner.stopping_conditions,
                                                                                  operation)

    @staticmethod
    async def sort_links(links):
        """
        Sort links by their score then by the order they are defined in an adversary profile
        """
        return sorted(links, key=lambda k: (-k.score))

    """ PRIVATE """

    async def _bucket_execute(self, operation, planner, links, condition_stop):
        """repeated code used in bucket_exhaustion()"""
        await operation.wait_for_links_completion(links)
        await self.update_stopping_condition_met(planner, operation)

    async def _stop_bucket_exhaustion(self, planner, operation, condition_stop):
        """ """
        if await operation.is_finished() or (condition_stop and planner.stopping_condition_met):
            return True
        return False

    @staticmethod
    async def _stopping_condition_met(facts, stopping_condition):
        for f in facts:
            if f.unique == stopping_condition.unique:
                return True
        return False

    async def _check_and_generate_cleanup_links(self, agent, operation):
        """
        repeated subroutine
        """
        agent_cleanup_links = []
        if agent.trusted:
            agent_cleanup_links = await self._generate_cleanup_links(operation=operation,
                                                                     agent=agent,
                                                                     link_status=operation.link_status())
        return agent_cleanup_links

    async def _generate_new_links(self, operation, agent, abilities, link_status):
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
        for l in links:
            for adjustment in [a for a in operation.source.adjustments if a.ability_id == l.ability.ability_id]:
                if operation.has_fact(trait=adjustment.trait, value=adjustment.value):
                    l.visibility.apply(adjustment)
                    l.status = l.states['HIGH_VIZ']
