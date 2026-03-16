import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.service.learning_svc import LearningService


class TestLearningServiceCache:
    def test_initial_state_dirty(self):
        with patch.object(LearningService, 'add_service', return_value=MagicMock()):
            with patch.object(LearningService, 'add_parsers', return_value=[]):
                svc = LearningService()
                assert svc._model_dirty is True
                assert svc._model_built_at == 0.0

    def test_invalidate_cache(self):
        with patch.object(LearningService, 'add_service', return_value=MagicMock()):
            with patch.object(LearningService, 'add_parsers', return_value=[]):
                svc = LearningService()
                svc._model_dirty = False
                svc._model_built_at = time.monotonic()
                svc.invalidate_model_cache()
                assert svc._model_dirty is True

    def test_skip_rebuild_when_cache_valid(self):
        with patch.object(LearningService, 'add_service', return_value=MagicMock()):
            with patch.object(LearningService, 'add_parsers', return_value=[]):
                svc = LearningService()
                svc._model_dirty = False
                svc._model_built_at = time.monotonic()
                mock_data_svc = MagicMock()
                mock_data_svc.locate = AsyncMock(return_value=[])
                svc.get_service = MagicMock(return_value=mock_data_svc)
                svc.get_config = MagicMock(return_value=3600)
                asyncio.run(svc.build_model())
                mock_data_svc.locate.assert_not_called()

    def test_rebuild_when_dirty(self):
        with patch.object(LearningService, 'add_service', return_value=MagicMock()):
            with patch.object(LearningService, 'add_parsers', return_value=[]):
                svc = LearningService()
                svc._model_dirty = True
                mock_data_svc = MagicMock()
                mock_data_svc.locate = AsyncMock(return_value=[])
                svc.get_service = MagicMock(return_value=mock_data_svc)
                svc.get_config = MagicMock(return_value=3600)
                asyncio.run(svc.build_model())
                mock_data_svc.locate.assert_called_once()
                assert svc._model_dirty is False
                assert svc._model_built_at > 0

    def test_rebuild_when_ttl_expired(self):
        """Rebuild must occur when cache TTL has expired even if not dirty."""
        with patch.object(LearningService, 'add_service', return_value=MagicMock()):
            with patch.object(LearningService, 'add_parsers', return_value=[]):
                svc = LearningService()
                ttl = 60
                svc._model_dirty = False
                # Set built-at to ttl+1 seconds in the past so it is expired.
                svc._model_built_at = time.monotonic() - (ttl + 1)
                mock_data_svc = MagicMock()
                mock_data_svc.locate = AsyncMock(return_value=[])
                svc.get_service = MagicMock(return_value=mock_data_svc)
                svc.get_config = MagicMock(return_value=ttl)
                asyncio.run(svc.build_model())
                mock_data_svc.locate.assert_called_once()
                assert svc._model_dirty is False

    def test_cache_ttl_as_string_is_coerced(self):
        """get_config() may return a string; it must be coerced to int without error."""
        with patch.object(LearningService, 'add_service', return_value=MagicMock()):
            with patch.object(LearningService, 'add_parsers', return_value=[]):
                svc = LearningService()
                svc._model_dirty = True
                mock_data_svc = MagicMock()
                mock_data_svc.locate = AsyncMock(return_value=[])
                svc.get_service = MagicMock(return_value=mock_data_svc)
                # Return TTL as a string (common when loaded from config files).
                svc.get_config = MagicMock(return_value='3600')
                asyncio.run(svc.build_model())
                mock_data_svc.locate.assert_called_once()
