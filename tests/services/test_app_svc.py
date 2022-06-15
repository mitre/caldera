import pytest

from app.utility.base_service import BaseService


@pytest.fixture
async def setup_app_service_test(setup_operations_api_test, test_agent, test_operation):
    operation = await BaseService.get_service('data_svc').locate('operations', {'id': test_operation['id']})
    operation.agents.append(test_agent)


@pytest.mark.usefixtures(
    "setup_app_service_test"
)
class TestAppService:
    async def test_mark_agent_as_untrusted_running_operation(self, test_operation):
        pass

    async def test_mark_agent_as_untrusted_paused_operation(self, test_agent):
        pass

    async def test_mark_agent_as_untrusted_out_of_time_operation(self, test_agent):
        pass

    async def test_mark_agent_as_untrusted_finished_operation(self, test_agent):
        pass

    async def test_mark_agent_as_untrusted_cleanup_operation(self, test_agent):
        pass
