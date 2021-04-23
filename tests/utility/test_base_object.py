import pytest

from app.utility.base_object import BaseObject
from app.utility.base_world import BaseWorld


@pytest.fixture
def base_world():
    BaseWorld.apply_config(
        name='main',
        config={
            'app.foo': 'foo',
            'app.bar': 'bar'
        }
    )

    yield BaseWorld

    BaseWorld.clear_config()


def test_replace_app_props(base_world):
    base_object = BaseObject()
    command = 'echo #{foo} #{app.foo} #{app.bar} #{app.foo.do.not.replace.me}'
    replaced = base_object.replace_app_props(BaseWorld.encode_string(command))
    expected = 'echo #{foo} foo bar #{app.foo.do.not.replace.me}'
    assert expected == BaseWorld.decode_bytes(replaced)
