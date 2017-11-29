from unittest import TestCase
import yaml
import cProfile as profile
import time

from caldera.app.simulate.world import World, MetaWorld
from caldera.app.logic.planner import PlannerContext
from caldera.app.operation.operation_steps import GetDomain, GetComputers, GetAdmin, Credentials, NetUse, Copy, \
    WMI_remote_pc
from caldera.app.simulate.simulate import Simulator
from caldera.app.operation.operation import _database_objs
from caldera.app.operation.step import OPShare
from caldera.app.simulate.generate import generate_circular
from caldera.app.logic.pydatalog_logic import DatalogContext as LogicContext


schema_yaml = """
OPConnection:
  dest: {ref: OPHost}
  src: {ref: OPHost}
OPCredential:
  domain: {ref: OPDomain}
  host: {ref: OPHost}
  password: string
  user: {ref: OPUser}
OPDomain:
  dns_domain: string
  hosts:
    list:
      backref: {OPHost: domain}
  windows_domain: string
OPFile:
  host: {ref: OPHost}
  path: string
  src_host: {ref: OPHost}
  src_path: string
OPHost:
  admins:
    list: {ref: OPUser}
  cached_creds:
    list: {ref: OPCredential}
  dc: bool
  dns_domain_name: string
  domain: {ref: OPDomain}
  fqdn: string
  hostname: string
  timedelta:
    backref: {OPTimeDelta: host}
  os_version: string
OPRat:
  elevated: bool
  executable: string
  host: {ref: OPHost}
  username: string
OPSchtask:
  arguments: string
  cred: {ref: OPCredential}
  exe_path: string
  name: string
  remote_host: {ref: OPHost}
  start_time: datetime
  status: string
  user: {ref: OPUser}
OPShare:
  dest_host: {ref: OPHost}
  share_name: string
  share_path: string
  src_host: {ref: OPHost}
OPTimeDelta:
  host: {ref: OPHost}
  microseconds: int
  seconds: int
OPUser:
  cred:
    backref: {OPCredential: user}
  domain: {ref: OPDomain}
  host: {ref: OPHost}
  is_group: bool
  sid: string
  username: string
"""

domain_yaml = """
- OPDomain:
    fields:
    - {windows_domain: $unique_greek}
    number: 1
- OPUser:
    fields:
    - {is_group: false}
    - {username: $unique_name}
    - {domain: $random_existing}
    - cred:
        $new:
          fields:
          - {user: $parent.id}
          - {domain: $parent.domain}
    number:
      $random: [__numhosts__, __numhosts__]
- OPHost:
    fields:
    - dc: {$bool_prob: 0.05}
    - {domain: $random_existing}
    - {fqdn: $unique_animal}
    - admins:
        $match: [domain, domain]
        $random_sample: 5
    - cached_creds: {$random_sample: 2}
    - timedelta:
        $new:
          fields:
          - {host: $parent.id}
    number:
      $random: [__numhosts__, __numhosts__]
"""


class TestSimulator(TestCase):
    def test_simulator(self):
        # generate a world
        schema = yaml.load(schema_yaml)
        domain = yaml.load(domain_yaml.replace('__numhosts__', '15'))
        world = World.generate_domain(schema, domain)

        generate_circular(world)

        # get the attacker planner
        planner = PlannerContext(LogicContext())

        for obj in _database_objs:
            primary = obj != OPShare
            planner.define_type(obj.__name__, primary=primary)

        for step in [GetDomain, GetComputers, GetAdmin, Credentials, NetUse, Copy, WMI_remote_pc]:
            planner.add_step(step)

        # create an attacker world
        meta_world = MetaWorld(world)
        attacker_world = meta_world.get_sub_world()

        start_host = world.get_objects_by_type('OPHost')[0]
        meta_world.know(attacker_world, start_host, ['fqdn'])
        meta_world.create(attacker_world, 'OPRat', {'elevated': True,
                                                    'executable': 'C:\\commander.exe',
                                                    'host': start_host,
                                                    'username': 'nt authority\\system'})

        # let it run
        simulator = Simulator(meta_world, schema)

        simulator.register_agent('attacker', planner, attacker_world)

        # expect it to run until the network is compromised
        ticks = 0
        profile_threshold = 10.0
        profile_state = "no"
        if profile_state == "full":
            pr = profile.Profile()
            pr.enable()
        while not simulator.all_agents_done():
            if profile_state == "profile":
                pr = profile.Profile()
                pr.enable()
            start_time = time.process_time()
            simulator.tick(ticks)
            duration = time.process_time() - start_time
            if profile_state == "profile":
                pr.disable()
                if duration > profile_threshold:
                    pr.dump_stats('profile.pstat')
                    profile_state = "success"
                    print("Got a profile")
            elif profile_state == "start" and duration > profile_threshold:
                profile_state = "profile"

            print("Step seconds: {}".format(duration))
            ticks += 1

        if profile_state == "full":
            pr.disable()
            pr.dump_stats('profile.pstat')
            print("Got a profile")

        # assert that there is a rat running on every host
        real_world = simulator.meta_world.get_real_world()
        for host in real_world.get_objects_by_type('OPHost'):
            found = False
            for rat in real_world.get_objects_by_type('OPRat'):
                if rat['host'] == host:
                    found = True
                    break

            if not found:
                for obj in attacker_world.get_all_objects():
                    print("{}{}".format(obj.typ, obj.to_dict()))
                self.fail("There was not a rat running on every host")

        print("Done after: {} ticks".format(ticks))

        planner.close()
