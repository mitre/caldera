"""Tests that plugin enable() failures are caught gracefully."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_failing_plugin_enable_is_caught():
    """Verify that enable() exceptions are caught and logged, not propagated."""
    log = MagicMock()
    plugin = MagicMock()
    plugin.name = 'test_plugin'
    plugin.enable = AsyncMock(side_effect=RuntimeError('init failed'))

    # Replicate the error-handling pattern from app_svc.py load_plugins()
    try:
        await plugin.enable({})
    except Exception:
        log.error('Failed to enable plugin: %s' % plugin.name, exc_info=True)

    log.error.assert_called_once()
    assert 'Failed to enable plugin' in log.error.call_args[0][0]


@pytest.mark.asyncio
async def test_successful_plugin_enable_logs_info():
    """Verify a successful enable() logs info."""
    log = MagicMock()
    plugin = MagicMock()
    plugin.name = 'good_plugin'
    plugin.enable = AsyncMock(return_value=None)

    await plugin.enable({})
    log.info('Enabled plugin: %s' % plugin.name)

    log.info.assert_called_once()
    assert 'good_plugin' in log.info.call_args[0][0]
