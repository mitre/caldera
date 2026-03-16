"""Tests that plugin enable() failures are caught gracefully in AppService.load_plugins()."""
import asyncio
import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_failing_plugin_enable_is_caught(tmp_path):
    """Verify that a plugin enable() raising an exception is caught and logged,
    not propagated, and does not prevent load_plugins from completing."""
    # Create a fake plugin directory with hook.py so load_plugins won't exit
    plugin_dir = tmp_path / 'plugins' / 'bad_plugin'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'hook.py').write_text('')

    mock_plugin = MagicMock()
    mock_plugin.name = 'bad_plugin'
    mock_plugin.load_plugin = MagicMock(return_value=True)
    mock_plugin.enable = AsyncMock(side_effect=RuntimeError('init failed'))

    with patch('app.service.app_svc.Plugin', return_value=mock_plugin), \
         patch('app.service.app_svc.os.path.isdir', return_value=True), \
         patch('app.service.app_svc.os.path.isfile', return_value=True):

        from app.service.app_svc import AppService
        app_svc = MagicMock(spec=AppService)
        app_svc.log = MagicMock()
        app_svc.get_config = MagicMock(return_value=['bad_plugin'])
        app_svc.get_services = MagicMock(return_value={})
        app_svc.get_service = MagicMock(return_value=MagicMock(store=AsyncMock()))
        app_svc._loaded_plugins = []

        # Call the real load_plugins method bound to our mock instance
        await AppService.load_plugins(app_svc, ['bad_plugin'])
        # Allow the created task to run
        await asyncio.sleep(0.1)

    app_svc.log.error.assert_called()
    error_msg = app_svc.log.error.call_args[0][0]
    assert 'Failed to enable plugin' in error_msg
    assert 'bad_plugin' in error_msg


@pytest.mark.asyncio
async def test_successful_plugin_enable_logs_info(tmp_path):
    """Verify a successful enable() logs an info message from the production code."""
    plugin_dir = tmp_path / 'plugins' / 'good_plugin'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'hook.py').write_text('')

    mock_plugin = MagicMock()
    mock_plugin.name = 'good_plugin'
    mock_plugin.load_plugin = MagicMock(return_value=True)
    mock_plugin.enable = AsyncMock(return_value=None)

    with patch('app.service.app_svc.Plugin', return_value=mock_plugin), \
         patch('app.service.app_svc.os.path.isdir', return_value=True), \
         patch('app.service.app_svc.os.path.isfile', return_value=True):

        from app.service.app_svc import AppService
        app_svc = MagicMock(spec=AppService)
        app_svc.log = MagicMock()
        app_svc.get_config = MagicMock(return_value=['good_plugin'])
        app_svc.get_services = MagicMock(return_value={})
        app_svc.get_service = MagicMock(return_value=MagicMock(store=AsyncMock()))
        app_svc._loaded_plugins = []

        await AppService.load_plugins(app_svc, ['good_plugin'])
        await asyncio.sleep(0.1)

    app_svc.log.info.assert_called()
    info_msg = app_svc.log.info.call_args[0][0]
    assert 'Enabled plugin' in info_msg
    assert 'good_plugin' in info_msg
