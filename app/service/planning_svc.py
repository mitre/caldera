from asyncio import gather
from app.objects.secondclass.c_link import Link
from app.utility.base_planning_svc import BasePlanningService


class PlanningService(BasePlanningService):

    def __init__(self):
        super().__init__()
        self.log = self.add_service('planning_svc', self)

    async def bucket_exhaustion(self, bucket, operation, agent=None):
        """
        TODO
        """
        gather(*[operation.apply(l) for l in await self.get_links(operation, bucket, agent)])  # dont have to use this as requires import, but wanted to see if worked
        await operation.wait_for_completion()

    async def default_next_bucket(self, current_bucket, state_machine):
        """
        TODO
        """
        idx = (state_machine.index(current_bucket) + 1) % len(state_machine)  # loops
        return state_machine[idx]
       
    async def get_links(self, operation, bucket=None, agent=None, trim=True, planner=None, stopping_conditions=None):
        """
        For an operation and agent combination, create links (that can be executed).
        When no agent is supplied, links for all agents are returned

        :param operation:
        :param bucket:
            'None' - no buckets, get all links for operation-agent
            'atomic' - no buckets, but resort to atomic ordering of links as specified in adversary
            '<bucket>' - get links for specified bucket
        :param agent:
        :param trim: call trim_links() on list of links before returning
        :param planner:
        :param stopping_conditions:
        :return: a list of links
        """
        if stopping_conditions and await self._check_stopping_conditions(operation, stopping_conditions):
            self.log.debug('Stopping conditions met. No more links will be generated!')
            planner.stopping_condition_met = True
            return []
        if bucket == "atomic":
            # atomic mode
            abilities = self._get_next_atomic_ability(operation=operation)
        elif bucket:
            # bucket 
            abilities = [ab for ab in operation.adversary.atomic_ordering if ab.bucket == bucket]
        else:
            # no mode
            abilities = operation.adversary.atomic_ordering
        links = []
        if agent:
            links.extend(await self.generate_and_trim_links(agent, operation, abilities, trim))
        else:
            for agent in operation.agents:
                links.extend(await self.generate_and_trim_links(agent, operation, abilities, trim))
        self.log.debug('Generated %s usable links' % (len(links)))
        if not operation.atomic_enabled and operation.auto_close and not links:
            operation.state = operation.states['FINISHED']
        return await self.sort_links(links)

    async def get_cleanup_links(self, operation, agent=None):
        """
        For a given operation, create all cleanup links.
        If agent is supplied, only return cleanup links for that agent.

        :param operation:
        :param agent:
        :return: None
        """
        links = []
        if agent:
            links.extend(await self._check_and_generate_cleanup_links(agent, operation))
        else:
            for agent in operation.agents:
                links.extend(await self._check_and_generate_cleanup_links(agent, operation))
        return reversed(links)

    async def generate_and_trim_links(self, agent, operation, abilities, trim=True):
        """
        repeated subroutine
        """
        agent_links = []
        if agent.trusted:
            agent_links = await self._generate_new_links(operation, agent, abilities, operation.link_status())
            await self._apply_adjustments(operation, agent_links)
            if trim:
                agent_links = await self.trim_links(operation, agent_links, agent)
        return agent_links

    @staticmethod
    async def sort_links(links):
        """
        Sort links by their score then by the order they are defined in an adversary profile
        """
        return sorted(links, key=lambda k: (-k.score))

    """ PRIVATE """

    @staticmethod
    def _get_next_atomic_ability(operation):
        if operation.last_ran is None:
            return [operation.adversary.atomic_ordering[0]]
        return operation.adversary.atomic_ordering[:(operation.adversary.atomic_ordering.index(operation.last_ran) + 2)]

    async def _check_stopping_conditions(self, operation, stopping_conditions):
        """
        Checks whether an operation has collected the proper facts to trigger this planner's stopping
        conditions

        :param operation:
        :param stopping_conditions:
        :return: True if all stopping conditions have been met, False if all stopping conditions have not
        been met
        """
        for sc in stopping_conditions:
            if not await self._stopping_condition_met(operation.all_facts(), sc):
                return False
        return True

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
            if a.test:
                links.append(
                    Link(operation=operation.id, command=a.test, paw=agent.paw, score=0, ability=a,
                         status=link_status, jitter=self.jitter(operation.jitter))
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
                lnk = Link(operation=operation.id, command=self.encode_string(variant), paw=agent.paw, cleanup=1,
                           ability=ability, score=0, jitter=2, status=link_status)
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
