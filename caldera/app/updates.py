import hashlib
import inspect
import mongoengine

from .engine.objects import Operation, CodedStep, AttackTactic, AttackTechnique, TechniqueMapping, Adversary
from .operation.operation import ServerOperation
from .operation import operation_steps
from .logic import logic, planner
from .operation.operation_steps import *

log = logging.getLogger(__name__)


def build_default_adversaries() -> None:
    for entry in Adversary.objects:
        if ((entry.name == 'Alice (Built-in)' and entry.protected) or
                (entry.name == 'Bob (Built-in)' and entry.protected) or
                (entry.name == 'Charlie (Built-in)' and entry.protected) or
                (entry.name == 'Lazarus Group (Built-in)' and entry.protected)):
            return

    alice_steplist = []
    alice = [x.__name__ for x in [Copy, Credentials, GetAdmin, GetComputers, GetDomain, NetUse, WMIRemoteProcessCreate]]
    bob_steplist = []
    bob = [x.__name__ for x in [Credentials, DirListCollection, ExfilAdversaryProfile, GetAdmin,
                                GetComputers, GetDomain, GetPrivEscSvcInfo, ServiceManipulateFileScLocal,
                                PsexecMove]]
    charlie_steplist = []
    charlie = [x.__name__ for x in [Copy, Credentials, GetAdmin, GetComputers, GetDomain, GetLocalProfiles,
                                    HKURunKeyPersist, NetUse, PassTheHashCopy, PassTheHashSc, SchtasksPersist,
                                    TasklistLocal, GetPrivEscSvcInfo, ServiceManipulateFileScLocal]]
    laz_steplist = []
    laz = [x.__name__ for x in [DirListCollection, ExfilAdversaryProfile, ScPersist, TasklistLocal,
                                TasklistRemote, GetLocalProfiles, HKURunKeyPersist, HKLMRunKeyPersist, Copy,
                                XCopy, SysteminfoLocal, SysteminfoRemote, GetDomain, GetLocalProfiles,
                                Timestomp, NetUse, WMIRemoteProcessCreate, Credentials, GetComputers, GetAdmin]]

    for entry in CodedStep.objects:
        if entry.name in alice:
            alice_steplist.append(entry)
        if entry.name in bob:
            bob_steplist.append(entry)
        if entry.name in charlie:
            charlie_steplist.append(entry)
        if entry.name in laz:
            laz_steplist.append(entry)

    steplists = {'Alice (Built-in)': alice_steplist,
                 'Bob (Built-in)': bob_steplist,
                 'Charlie (Built-in)': charlie_steplist,
                 'Lazarus Group (Built-in)': laz_steplist}

    for name, steplist in steplists.items():
        adv = {'name': name,
               'exfil_method': 'rawtcp',
               'exfil_port': '8889',
               'exfil_address': 'x.x.x.x',
               'artifactlists': [],
               'steps': steplist,
               'protected': True}
        Adversary(**adv).save()


async def start_operations(rebuild_mappings=False) -> None:
    """
    Monitors the database for new operations and executes them
    Returns:
        Does not return
    """
    # remove steps that don't exist anymore
    for step in CodedStep.objects(name__nin=[x.__name__ for x in operation_steps.all_steps]):
        log.info("Removing old step {}".format(step.name))
        step.delete()

    # Analyze steps
    for step in operation_steps.all_steps:
        new_step = False
        try:
            db_step = CodedStep.objects.get(name=step.__name__)
        except mongoengine.errors.DoesNotExist:
            new_step = True
            db_step = CodedStep(name=step.__name__).save()

        step_source = inspect.getsource(step)
        sha1 = hashlib.sha1()
        sha1.update(step_source.encode('utf8'))

        update_object = False
        try:
            if db_step.source_hash != sha1.digest():
                update_object = True
        except AttributeError:
            update_object = True

        if update_object:
            # convert step to logic
            log.info("Updating logical definition of step: '{}'".format(step.__name__))

            action = logic.convert_to_action(step, planner.PlannerContext.unique_count)

            updates = action.build_database_dict()
            updates['source_hash'] = sha1.digest()
            updates['summary'] = step.__doc__
            updates['display_name'] = step.display_name
            updates['coded_name'] = step.coded_name
            updates['default_mapping'] = [TechniqueMapping(tactic=AttackTactic.objects.get(name=x[1]),
                                                           technique=AttackTechnique.objects.get(technique_id=x[0]))
                                          for x in step.attack_mapping]
            updates["cddl"] = step.cddl
            if rebuild_mappings or new_step:
                updates['mapping'] = updates['default_mapping']
            db_step.modify(**updates)

    build_default_adversaries()

    while True:
        ran_op = False
        # finish running operations that are started but not complete
        for operation in Operation.objects(status__nin=["start", "complete"]):
            s = ServerOperation(operation)
            await s.loop()
            ran_op = True

        # start any pending operation
        for operation in Operation.objects(status="start"):
            s = ServerOperation(operation)
            await s.loop()
            ran_op = True

        if not ran_op:
            # if we didn't run any operations at all on this loop, block on the db so we aren't busy waiting
            await Operation.wait_next()
