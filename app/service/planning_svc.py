from app.objects.secondclass.c_link import Link
from app.service.interfaces.i_planning_svc import PlanningServiceInterface
from app.utility.base_planning_svc import BasePlanningService
from app.objects.secondclass.c_fact import Fact



class PlanningService(PlanningServiceInterface, BasePlanningService):

    def __init__(self, global_variable_owners=None):
        super().__init__(global_variable_owners=global_variable_owners)
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
            operation has been stopped (by user) after all bucket links
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
            for s_link in links:
                l_id = await operation.apply(s_link)
                if batch:
                    l_ids.append(l_id)
                else:
                    if await self.wait_for_links_and_monitor(planner, operation, [l_id], condition_stop):
                        return
            if batch:
                if await self.wait_for_links_and_monitor(planner, operation, l_ids, condition_stop):
                    return
            

    async def wait_for_links_and_monitor(self, planner, operation, link_ids, condition_stop):
        """Wait for link completion, update stopping conditions and
        (optionally) stop bucket execution if stopping conditions are met.

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
        await operation.wait_for_links_completion(link_ids)
        await self.update_stopping_condition_met(planner, operation)
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

    async def execute_planner(self, planner, publish_transitions=True):
        """Execute planner.

        This method will run the planner, progressing from bucket to
        bucket, as specified by the planner.

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
        :param publish_transitions: flag to publish bucket transitions as
          events to the event service
        :type publish_transitions: bool
        """
        async def _publish_bucket_transition(bucket):
            """ subroutine to publish bucket transitions to event_svc"""
            await self.get_service('event_svc').fire_event(
                exchange='planner', queue='bucket_transition',
                bucket=bucket,
                operation_id=planner.operation.id,
                operation_name=planner.operation.name)

        while planner.next_bucket is not None and not (planner.stopping_condition_met and planner.stopping_conditions) \
                and not await planner.operation.is_finished():
            if publish_transitions:
                await _publish_bucket_transition(planner.next_bucket)
            await getattr(planner, planner.next_bucket)()
            await self.update_stopping_condition_met(planner, planner.operation)
        if publish_transitions:
            await _publish_bucket_transition("(planner completed)")

    async def get_links(self, operation, buckets=None, agent=None, trim=True):
        """Generate links for use in an operation

        For an operation and agent combination, create links (that can
        be executed). When no agent is supplied, links for all agents
        are returned.

        :param operation: Operation to generate links for
        :type operation: Operation
        :param buckets: Buckets containing abilities. If 'None', get all links
            for given operation, agent, and trim setting. If a list of buckets
            is provided, then get links for specified buckets for given
            operation and trim setting. Defaults to None.
        :type buckets: list(string), optional
        :param agent: Agent to generate links for, defaults to None
        :type agent: Agent, optional
        :param trim: call trim_links() on list of links before
            returning, defaults to True
        :type trim: bool, optional
        :return: a list of links sorted by score and atomic ordering
        """
        self.log.debug(
            'Generating links for operation %s, agent %s, buckets %s, trim %s',
            operation.name, getattr(agent, "paw", None), buckets, trim
        )

        raw_steps = operation.adversary.atomic_ordering
        step_entries = []
        unique_ids = set()
        self.log.debug(f' Raw steps from adversary profile: {raw_steps}')

        for idx, step in enumerate(raw_steps):
            if isinstance(step, str):
                ability_id = step
                metadata = {}
            else:
                ability_id = step.get('ability_id')
                metadata = step.get('metadata', {})

            step_entries.append({
                'step_idx': idx,
                'ability_id': ability_id,
                'metadata': metadata
            })
            unique_ids.add(ability_id)
            self.log.debug(f' Processed step entry: {step_entries[-1]}')

        all_abilities = await self.get_service('data_svc').locate('abilities', match=dict(ability_id=tuple(unique_ids)))
        ability_map = {a.ability_id: a for a in all_abilities}

        # Build step objects with resolved abilities
        steps_with_abilities = []
        for step in step_entries:
            ability = ability_map.get(step['ability_id'])
            if not ability:
                continue
            steps_with_abilities.append({
                'step_idx': step['step_idx'],
                'ability': ability,
                'metadata': step['metadata']
            })
            self.log.debug(f' Processed step with ability: {steps_with_abilities[-1]}')

        # Optionally filter by buckets
        if buckets:
            steps_with_abilities = [
                s for s in steps_with_abilities
                if any(bucket in s['ability'].buckets for bucket in buckets)
            ]

        links = []
        if agent:
            links.extend(await self.generate_and_trim_links(agent, operation, steps_with_abilities, trim))
            self.log.debug('Generated %s links for operation %s (agent: %s)', len(links), operation.name, agent.paw)
        else:
            agent_links = []
            for ag in operation.agents:
                agent_links.append(await self.generate_and_trim_links(ag, operation, steps_with_abilities, trim))
            self.log.debug('Generated %s link groups for operation %s', len(agent_links), operation.name)
            links = await self._remove_links_of_duplicate_singletons(agent_links)
            self.log.debug('Removed duplicate singleton links, %s links remain for operation %s', len(links), operation.name)

        self.log.debug('Generated %s usable links', len(links))
        self.log.debug('Final link list: %s', [link.ability.ability_id for link in links])
        sorted_links = await self.sort_links(links)
        self.log.debug(f' Sorted links: {[link.ability.ability_id for link in sorted_links]}')
        return sorted_links

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

    async def generate_and_trim_links(self, agent, operation, steps_with_abilities, trim=True):
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
            self.log.debug('Generating and trimming links for agent: %s', agent.paw)

            agent_links = await self._generate_new_links(operation, agent, steps_with_abilities, operation.link_status())
            self.log.debug('Generated %s links for agent: %s', len(agent_links), agent.paw)
            await self._apply_adjustments(operation, agent_links)
            if trim:
                agent_links = await self.trim_links(operation, agent_links, agent)
                self.log.debug('Trimmed to %s usable links for agent: %s', len(agent_links), agent.paw)
            self.log.debug('Final link list for agent %s: %s', agent.paw, [link.ability.ability_id for link in agent_links])
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
        all_facts = await operation.all_facts()
        for sc in stopping_conditions:
            if not await self._stopping_condition_met(all_facts, sc):
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

    async def _stop_bucket_exhaustion(self, planner, operation, condition_stop):
        """Determine whether to continue running the bucket.

        Returns True if:
            - Operation is finished
            - If `condition_stop` is True, and one of the planner's
            stopping conditions has been met.

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

    async def _generate_new_links(self, operation, agent, steps_with_abilities, link_status):
        self.log.debug('[link_gen] Using adversary metadata: %s', operation.adversary.metadata)
        # Normalize metadata from atomic_ordering into .metadata if not already present
        step_metadata = {}
        for idx, step in enumerate(operation.adversary.atomic_ordering):
            if isinstance(step, dict):
                meta = step.get('metadata')
                if meta:
                    step_metadata[str(idx)] = meta
        operation.adversary.metadata = step_metadata
        self.log.debug('[link_gen] Normalized adversary metadata: %s', operation.adversary.metadata)
        links = []

        for step in steps_with_abilities:
            idx = step['step_idx']
            ability = step['ability']
            step_meta = step.get('metadata', {})

            self.log.debug('Processing step idx %s with ability_id %s', idx, ability.ability_id)

            supported_abilities = await agent.capabilities([ability])
            if ability.ability_id not in [a.ability_id for a in supported_abilities]:
                self.log.debug('Ability_id %s not supported by agent %s', ability.ability_id, agent.paw)
                continue

            executor = await agent.get_preferred_executor(ability)
            if not executor:
                self.log.debug('No executor found for ability_id %s on agent %s', ability.ability_id, agent.paw)
                continue

            self.log.debug('Using executor %s for ability_id %s on agent %s', executor.name, ability.ability_id, agent.paw)
            if executor.HOOKS and executor.language in executor.HOOKS:
                await executor.HOOKS[executor.language](ability, executor)

            # --- Collect metadata facts (if any) ---
            fact_strings = []
            fact_strings.extend(step_meta.get('facts', []))  # legacy flat format
            executor_platform = executor.platform
            self.log.debug('Executor platform: %s', executor_platform)
            exec_facts = step_meta.get('executor_facts', {}).get(executor_platform, [])
            self.log.debug('Executor facts: %s', exec_facts)
            fact_strings.extend(exec_facts)

            facts = []
            for f in fact_strings:
                try:
                    trait = f['trait']
                    value = f['value']
                    facts.append({trait.strip(): value.strip('" ')})
                except Exception as e:
                    self.log.warning('Skipping malformed fact: %s (%s)', f, e)
            self.log.debug('Using facts for step idx %s: %s', idx, facts)

            # --- Build the link ---
            link = Link.load(dict(
                paw=agent.paw,
                score=0,
                ability=ability,
                executor=executor,
                status=link_status,
                jitter=self.jitter(operation.jitter)
            ))
            link.step_idx = idx

            injected = None

            if facts:
                self.log.debug('Injecting using metadata facts for step idx %s', idx)
                for f in facts:
                    for trait, value in f.items():
                        link.used.append(Fact(trait=trait, value=value, source=operation.id))
                injected = await self.inject_facts(executor.test, facts)
            else:
                self.log.debug('No metadata facts found; falling back to legacy fact injection for step idx %s', idx)
                injected, _, used = await self._build_single_test_variant(executor.test, [], executor.name)
                self.log.debug('after build_single_test injected command: %s', injected)
                for f in used:
                    link.used.append(f)

            # # If unresolved placeholders still exist, skip this step
            # if '#{' in injected:
            #     self.log.debug('Unresolved placeholders remain after injection for step idx %s; skipping', idx)
            #     continue

            link.command = self.encode_string(injected)
            self.log.debug('Injected command template: %s', executor.test)
            self.log.debug('Final injected command: %s', injected)
            self.log.debug('Final command: %s', link.command)

            links.append(link)

        return links

    
    async def inject_facts(self, template, fact_strings):
        """Replace #{trait} placeholders in the template using trait:value fact strings or dicts"""
        self.log.debug('Injecting facts into template: %s with fact strings: %s', template, fact_strings)
        substitutions = {}

        for entry in fact_strings:
            try:
                if isinstance(entry, dict):
                    trait, value = next(iter(entry.items()))
                elif isinstance(entry, str):
                    trait, value = entry.split(':', 1)
                else:
                    continue
                substitutions[trait.strip()] = value.strip()
            except Exception as e:
                self.log.warning('Failed to parse fact: %s (%s)', entry, e)

        self.log.debug('Fact substitutions: %s', substitutions)
        self.log.debug('Original template: %s', template)

        for trait, value in substitutions.items():
            placeholder = f'#{{{trait}}}'
            if placeholder in template:
                self.log.debug('[inject_facts] Replacing %s with %s', placeholder, value)
            else:
                self.log.debug('[inject_facts] Warning: placeholder %s not found in template', placeholder)
            template = template.replace(placeholder, value)

        self.log.debug('Final injected template: %s', template)
        return template

    
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
        cleanup_commands = set()
        for link in operation.chain:
            if link.paw != agent.paw:
                continue

            for cleanup in link.executor.cleanup:
                decoded_cmd = agent.replace(self.encode_string(cleanup), file_svc=self.get_service('file_svc'))
                variant, _, _ = await self._build_single_test_variant(decoded_cmd, link.used, link.executor.name)
                cleanup_command = self.encode_string(variant)
                if cleanup_command and cleanup_command not in cleanup_commands:
                    cleanup_commands.add(cleanup_command)
                    lnk = Link.load(dict(command=cleanup_command, paw=agent.paw, cleanup=1,
                                         ability=link.ability, executor=link.executor, score=0, jitter=2,
                                         status=link_status))
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
        for a_link in links:
            for adjustment in [a for a in operation.source.adjustments if a.ability_id == a_link.ability.ability_id]:
                if operation.has_fact(trait=adjustment.trait, value=adjustment.value):
                    a_link.visibility.apply(adjustment)
                    a_link.status = a_link.states['HIGH_VIZ']
