import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.utility.base_planning_svc import BasePlanningService


def _make_link(timeout):
    """Build a minimal mock link with an executor.timeout."""
    link = MagicMock()
    link.host = 'testhost'
    link.command = ''
    link.executor.timeout = timeout
    link.executor.name = 'sh'
    return link


def _make_svc():
    svc = BasePlanningService.__new__(BasePlanningService)
    svc._global_variable_owners = []
    svc._cached_requirement_modules = {}
    svc._max_link_timeout = BasePlanningService.MAX_LINK_TIMEOUT_DEFAULT
    svc.log = MagicMock()
    return svc


class TestLinkTimeoutCapping:
    def test_default_max_timeout_constant(self):
        assert BasePlanningService.MAX_LINK_TIMEOUT_DEFAULT == 600

    @pytest.mark.asyncio
    async def test_timeout_capped_to_max(self):
        """Links with timeout above max_link_timeout must be capped."""
        svc = _make_svc()
        link = _make_link(timeout=1200)
        agent = MagicMock()
        agent.replace = MagicMock(return_value='')
        agent.host = 'testhost'

        with patch.object(type(svc), 'get_config', return_value=600), \
             patch.object(type(svc), 'get_service', return_value=None), \
             patch.object(svc, '_build_relevant_facts', new_callable=AsyncMock, return_value=[]):
            await svc.add_test_variants([link], agent)

        assert link.executor.timeout == 600

    @pytest.mark.asyncio
    async def test_timeout_not_capped_when_below_max(self):
        """Links with timeout below max_link_timeout must not be changed."""
        svc = _make_svc()
        link = _make_link(timeout=300)
        agent = MagicMock()
        agent.replace = MagicMock(return_value='')
        agent.host = 'testhost'

        with patch.object(type(svc), 'get_config', return_value=600), \
             patch.object(type(svc), 'get_service', return_value=None), \
             patch.object(svc, '_build_relevant_facts', new_callable=AsyncMock, return_value=[]):
            await svc.add_test_variants([link], agent)

        assert link.executor.timeout == 300

    @pytest.mark.asyncio
    async def test_none_config_falls_back_to_default(self):
        """When get_config returns None, the default MAX_LINK_TIMEOUT_DEFAULT is used."""
        svc = _make_svc()
        link = _make_link(timeout=9999)
        agent = MagicMock()
        agent.replace = MagicMock(return_value='')
        agent.host = 'testhost'

        with patch.object(type(svc), 'get_config', return_value=None), \
             patch.object(type(svc), 'get_service', return_value=None), \
             patch.object(svc, '_build_relevant_facts', new_callable=AsyncMock, return_value=[]):
            await svc.add_test_variants([link], agent)

        assert link.executor.timeout == BasePlanningService.MAX_LINK_TIMEOUT_DEFAULT

    @pytest.mark.asyncio
    async def test_empty_links_does_not_raise(self):
        """add_test_variants with an empty list and trim_unset_variables=True must not raise.

        Regression test: previously the debug log after the loop referenced 'link'
        which was unbound when links=[], causing UnboundLocalError.
        """
        svc = _make_svc()
        agent = MagicMock()
        agent.host = 'testhost'

        with patch.object(type(svc), 'get_config', return_value=600):
            # This must not raise UnboundLocalError
            result = await svc.add_test_variants(
                [], agent, trim_unset_variables=True
            )
        assert result == []
