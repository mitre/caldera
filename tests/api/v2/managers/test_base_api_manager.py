import marshmallow as ma

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.utility.base_object import BaseObject


class StubDataService:
    def __init__(self):
        self.ram = {}


class TestSchema(ma.Schema):
    __test__ = False

    name = ma.fields.String()
    value = ma.fields.String()

    @ma.post_load()
    def build_test_object(self, data, **kwargs):
        return None if kwargs.get('partial') else TestObject(**data)


class TestObject(FirstClassObjectInterface, BaseObject):
    __test__ = False

    schema = TestSchema()
    display_schema = TestSchema()

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    def __init__(self, name, value):
        super().__init__()
        self.name = name
        self.value = value

    def store(self, ram):
        ram_key = 'tests'
        existing = self.retrieve(ram[ram_key], self.unique)
        if not existing:
            ram[ram_key].append(self)
            return self.retrieve(ram[ram_key], self.unique)
        existing.update('name', self.name)
        existing.update('value', self.value)
        return existing


def test_find_objects(agent):
    stub_data_svc = StubDataService()
    stub_data_svc.ram['agents'] = [
        agent(paw='agent0', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent1', sleep_min=2, sleep_max=5, watchdog=0)
    ]
    manager = BaseApiManager(data_svc=stub_data_svc)

    agents = list(manager.find_objects('agents'))

    assert len(agents) == len(stub_data_svc.ram['agents'])


def test_find_objects_with_search(agent):
    search_property = 'sleep_min'
    search_value = 2

    stub_data_svc = StubDataService()
    stub_data_svc.ram['agents'] = [
        agent(paw='agent0', sleep_min=1, sleep_max=5, watchdog=0),
        agent(paw='agent1', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent2', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent3', sleep_min=3, sleep_max=5, watchdog=0),
    ]
    manager = BaseApiManager(data_svc=stub_data_svc)

    search = {search_property: search_value}
    agents = list(manager.find_objects('agents', search=search))

    assert len(agents) == 2
    for agent in agents:
        assert getattr(agent, search_property) == search_value


def test_find_object(agent):
    search_property = 'paw'
    search_value = 'agent0'

    test_agent = agent(paw='agent0', sleep_min=1, sleep_max=5, watchdog=0)
    stub_data_svc = StubDataService()
    stub_data_svc.ram['agents'] = [
        agent(paw='agent1', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent2', sleep_min=2, sleep_max=5, watchdog=0),
        test_agent,
    ]
    manager = BaseApiManager(data_svc=stub_data_svc)

    search = {search_property: search_value}
    agents = list(manager.find_objects('agents', search=search))

    assert len(agents) == 1
    assert agents[0] == test_agent


def test_dump(data_svc, agent):
    test_agent = agent(sleep_min=2, sleep_max=5, watchdog=0)
    dumped_agent = test_agent.schema.dump(test_agent)

    manager = BaseApiManager(data_svc=data_svc)
    manager_dumped_agent = manager.dump_object_with_filters(test_agent)

    for key in manager_dumped_agent:
        assert manager_dumped_agent[key] == dumped_agent[key]


def test_dump_with_exclude(data_svc, agent):
    exclude_key = 'paw'

    test_agent = agent(sleep_min=2, sleep_max=5, watchdog=0)
    dumped_agent = test_agent.schema.dump(test_agent)

    manager = BaseApiManager(data_svc=data_svc)
    manager_dumped_agent = manager.dump_object_with_filters(test_agent, exclude=[exclude_key])

    assert exclude_key in dumped_agent
    assert exclude_key not in manager_dumped_agent
    for key in manager_dumped_agent:
        assert manager_dumped_agent[key] == dumped_agent[key]


def test_dump_with_include(data_svc, agent):
    include_key = 'paw'

    test_agent = agent(sleep_min=2, sleep_max=5, watchdog=0)
    dumped_agent = test_agent.schema.dump(test_agent)

    manager = BaseApiManager(data_svc=data_svc)
    manager_dumped_agent = manager.dump_object_with_filters(test_agent, include=[include_key])

    assert include_key in dumped_agent
    assert include_key in manager_dumped_agent
    assert len(manager_dumped_agent.keys()) == 1
    assert manager_dumped_agent[include_key] == dumped_agent[include_key]


def test_find_and_dump_objects_with_sort(agent):
    sort_property = 'paw'

    stub_data_svc = StubDataService()
    stub_data_svc.ram['agents'] = [
        agent(paw='agent5', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent1', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent3', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent0', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent4', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent2', sleep_min=2, sleep_max=5, watchdog=0),
    ]
    manager = BaseApiManager(data_svc=stub_data_svc)

    dumped_agents = manager.find_and_dump_objects('agents', sort=sort_property)

    assert len(dumped_agents) == len(stub_data_svc.ram['agents'])
    prev_paw = None
    for dumped_agent in dumped_agents:
        assert not prev_paw or dumped_agent[sort_property] > prev_paw
        prev_paw = dumped_agent[sort_property]


def test_find_and_dump_object(agent):
    test_agent = agent(paw='agent0', sleep_min=1, sleep_max=5, watchdog=0)
    stub_data_svc = StubDataService()
    stub_data_svc.ram['agents'] = [test_agent]
    manager = BaseApiManager(data_svc=stub_data_svc)

    dumped_agent = manager.find_and_dump_object('agents')

    assert dumped_agent == test_agent.display


def test_store_json_as_schema():
    stub_data_svc = StubDataService()
    stub_data_svc.ram['tests'] = []
    manager = BaseApiManager(data_svc=stub_data_svc)

    data = {'name': 'test_name', 'value': 'test_value'}
    obj = manager.store_json_as_schema(TestSchema, data)

    assert obj.name == 'test_name' and obj.value == 'test_value'


def test_update_object(agent):
    stub_data_svc = StubDataService()
    stub_data_svc.ram['tests'] = [
        TestObject(name='name0', value='value0'),
        TestObject(name='name1', value='value1'),
    ]
    manager = BaseApiManager(data_svc=stub_data_svc)

    data = {'value': 'value1'}
    search = {'name': 'name0'}
    manager.update_object('tests', data, search)

    assert len(stub_data_svc.ram['tests']) == 2
    for test_obj in stub_data_svc.ram['tests']:
        assert test_obj.value == 'value1'
