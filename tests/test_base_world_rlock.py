import threading
import pytest
from app.utility.base_world import BaseWorld


@pytest.fixture(autouse=True)
def setup_config():
    BaseWorld.apply_config('main', {'test_key': 'test_value'})
    yield
    BaseWorld.clear_config()


class TestBaseWorldRLock:
    def test_config_lock_exists(self):
        assert isinstance(BaseWorld._app_config_lock, type(threading.RLock()))

    def test_apply_and_get_config(self):
        BaseWorld.apply_config('main', {'key1': 'value1'})
        assert BaseWorld.get_config('key1') == 'value1'

    def test_set_config(self):
        BaseWorld.set_config('main', 'new_key', 'new_value')
        assert BaseWorld.get_config('new_key') == 'new_value'

    def test_clear_config(self):
        BaseWorld.clear_config()
        BaseWorld.apply_config('main', {})
        assert BaseWorld.get_config('test_key') is None

    def test_concurrent_access(self):
        errors = []

        def writer():
            try:
                for i in range(100):
                    BaseWorld.set_config('main', f'key_{i}', f'value_{i}')
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(100):
                    BaseWorld.get_config('test_key')
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(5)]
        threads += [threading.Thread(target=reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
