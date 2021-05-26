from app.api.v2.managers.base_api_manager import BaseApiManager


class StubDataService:
    def __init__(self):
        self.ram = {}


def test_dump(data_svc, agent):
    test_agent = agent(sleep_min=2, sleep_max=5, watchdog=0)
    dumped_agent = test_agent.schema.dump(test_agent)

    manager = BaseApiManager(data_svc=data_svc)
    manager_dumped_agent = manager.dump_with_include_exclude(test_agent)

    for key in manager_dumped_agent:
        assert manager_dumped_agent[key] == dumped_agent[key]


def test_dump_with_exclude(data_svc, agent):
    exclude_key = 'paw'

    test_agent = agent(sleep_min=2, sleep_max=5, watchdog=0)
    dumped_agent = test_agent.schema.dump(test_agent)

    manager = BaseApiManager(data_svc=data_svc)
    manager_dumped_agent = manager.dump_with_include_exclude(test_agent, exclude=[exclude_key])

    assert exclude_key in dumped_agent
    assert exclude_key not in manager_dumped_agent
    for key in manager_dumped_agent:
        assert manager_dumped_agent[key] == dumped_agent[key]


def test_dump_with_include(data_svc, agent):
    include_key = 'paw'

    test_agent = agent(sleep_min=2, sleep_max=5, watchdog=0)
    dumped_agent = test_agent.schema.dump(test_agent)

    manager = BaseApiManager(data_svc=data_svc)
    manager_dumped_agent = manager.dump_with_include_exclude(test_agent, include=[include_key])

    assert include_key in dumped_agent
    assert include_key in manager_dumped_agent
    assert len(manager_dumped_agent.keys()) == 1
    assert manager_dumped_agent[include_key] == dumped_agent[include_key]


def test_get_objects(agent):
    stub_data_svc = StubDataService()
    stub_data_svc.ram['agents'] = [
        agent(paw='agent0', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent1', sleep_min=2, sleep_max=5, watchdog=0)
    ]
    manager = BaseApiManager(data_svc=stub_data_svc)

    dumped_agents = manager.get_objects_with_filters('agents')

    assert len(dumped_agents) == len(stub_data_svc.ram['agents'])


def test_get_objects_with_search(agent):
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
    dumped_agents = manager.get_objects_with_filters('agents', search=search)

    assert len(dumped_agents) == 2
    for dumped_agent in dumped_agents:
        assert dumped_agent[search_property] == search_value


def test_get_objects_with_sort(agent):
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

    dumped_agents = manager.get_objects_with_filters('agents', sort=sort_property)

    assert len(dumped_agents) == len(stub_data_svc.ram['agents'])
    prev_paw = None
    for dumped_agent in dumped_agents:
        assert not prev_paw or dumped_agent[sort_property] > prev_paw
        prev_paw = dumped_agent[sort_property]


def test_get_object(agent):
    search_property = 'paw'
    search_value = 'agent0'

    test_agent = agent(paw='agent0', sleep_min=1, sleep_max=5, watchdog=0)
    stub_data_svc = StubDataService()
    stub_data_svc.ram['agents'] = [
        test_agent,
        agent(paw='agent1', sleep_min=2, sleep_max=5, watchdog=0),
        agent(paw='agent2', sleep_min=2, sleep_max=5, watchdog=0),
    ]
    manager = BaseApiManager(data_svc=stub_data_svc)

    search = {search_property: search_value}
    dumped_agent = manager.get_object_with_filters('agents', search=search)

    assert dumped_agent == test_agent.display
