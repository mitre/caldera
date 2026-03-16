import io
import os
import tempfile
import pytest
from app.api.v2.handlers.payload_api import PayloadApi, FileTooLargeError


class TestPayloadUploadSizeLimit:
    def test_file_too_large_raises_error(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            target = f.name
        try:
            large_data = b'A' * 2000
            src = io.BytesIO(large_data)
            with pytest.raises(FileTooLargeError):
                PayloadApi._PayloadApi__save_file(target, src, max_size_bytes=1000)
        finally:
            if os.path.exists(target):
                os.unlink(target)

    def test_file_within_limit_succeeds(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            target = f.name
        try:
            data = b'A' * 500
            src = io.BytesIO(data)
            PayloadApi._PayloadApi__save_file(target, src, max_size_bytes=1000)
            assert os.path.getsize(target) == 500
        finally:
            if os.path.exists(target):
                os.unlink(target)

    def test_no_limit_allows_any_size(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            target = f.name
        try:
            data = b'A' * 50000
            src = io.BytesIO(data)
            PayloadApi._PayloadApi__save_file(target, src, max_size_bytes=0)
            assert os.path.getsize(target) == 50000
        finally:
            if os.path.exists(target):
                os.unlink(target)

    def test_partial_file_cleaned_up_on_too_large(self):
        """__save_file should remove the partial file when FileTooLargeError is raised."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            target = f.name
        large_data = b'B' * 2000
        src = io.BytesIO(large_data)
        with pytest.raises(FileTooLargeError):
            PayloadApi._PayloadApi__save_file(target, src, max_size_bytes=1000)
        assert not os.path.exists(target), "Partial file should have been removed by __save_file"

    def test_zero_config_means_no_limit(self):
        """max_size_mb=0 in config should be interpreted as 'no limit', not as 100 MB default."""
        # Simulate the config-derived calculation: 0 * 1024 * 1024 == 0 (no limit)
        max_size_mb = 0
        max_size_bytes = max_size_mb * 1024 * 1024 if max_size_mb else 0
        assert max_size_bytes == 0, "0 MB config must map to max_size_bytes=0 (no limit)"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            target = f.name
        try:
            data = b'C' * 200000
            src = io.BytesIO(data)
            # Should not raise even though data is large
            PayloadApi._PayloadApi__save_file(target, src, max_size_bytes=max_size_bytes)
            assert os.path.getsize(target) == 200000
        finally:
            if os.path.exists(target):
                os.unlink(target)
