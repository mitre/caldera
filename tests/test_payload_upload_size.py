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
