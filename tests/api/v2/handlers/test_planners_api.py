import pytest

from http import HTTPStatus

from app.objects.c_planner import Planner
from app.utility.base_service import BaseService


@pytest.fixture
def test_planner(event_loop, api_v2_client):
    planner = Planner(name="123test planner", planner_id="123", description="a test planner", plugin="planner")
    event_loop.run_until_complete(BaseService.get_service('data_svc').store(planner))
    return planner


@pytest.fixture
def test_planner_2(event_loop, api_v2_client):
    planner = Planner(name="atomic", planner_id="456", description="an alphabetically superior test planner (fake)",
                      plugin="planner")
    event_loop.run_until_complete(BaseService.get_service('data_svc').store(planner))
    return planner


@pytest.fixture
def expected_test_planner_dump(test_planner):
    return test_planner.display_schema.dump(test_planner)


class TestPlannersApi:
    async def test_get_planners(self, api_v2_client, api_cookies, test_planner, expected_test_planner_dump):
        resp = await api_v2_client.get('/api/v2/planners', cookies=api_cookies)
        planners_list = await resp.json()
        assert len(planners_list) == 1
        planner_dict = planners_list[0]
        assert planner_dict == expected_test_planner_dump

    async def test_unauthorized_get_planners(self, api_v2_client, test_planner):
        resp = await api_v2_client.get('/api/v2/planners')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_planner_by_id(self, api_v2_client, api_cookies, test_planner, expected_test_planner_dump):
        resp = await api_v2_client.get('/api/v2/planners/123', cookies=api_cookies)
        planner_dict = await resp.json()
        assert planner_dict == expected_test_planner_dump

    async def test_unauthorized_get_planner_by_id(self, api_v2_client, test_planner):
        resp = await api_v2_client.get('/api/v2/planners/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_nonexistent_planner_by_id(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/planners/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_planner_defaults(self, api_v2_client, api_cookies, test_planner, test_planner_2):
        resp = await api_v2_client.get('/api/v2/planners', cookies=api_cookies)
        planners_list = await resp.json()
        assert len(planners_list) == 2
        assert planners_list[0]["id"] == "456"
        assert planners_list[0]["name"][0] > planners_list[1]["name"][0]  # prove that this wasn't an alphabetical sort
