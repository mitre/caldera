import pytest

from app.utility.base_object import BaseObject
from app.utility.base_object import AppConfigGlobalVariableIdentifier
from app.utility.base_world import BaseWorld


@pytest.fixture
def base_world():
    BaseWorld.apply_config(
        name='main',
        config={
            'app.foo': 'foo',
            'app.bar': 'bar',
            'auth.baz': 'not an app. item'
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


def test_is_global_variable_identifies_variable_starting_with_app(base_world):
    global_variable_owner = AppConfigGlobalVariableIdentifier()
    assert global_variable_owner.is_global_variable('app.foo')
    assert global_variable_owner.is_global_variable('app.bar')


def test_is_global_variable_identifies_variable_ignores_non_config_key(base_world):
    global_variable_owner = AppConfigGlobalVariableIdentifier()

    # Starts with 'app.' but not a configuration key
    assert global_variable_owner.is_global_variable('app.this.does.not.exist') is False


def test_is_global_variable_identifies_variable_ignores_config_keys_not_starting_with_app(base_world):
    global_variable_owner = AppConfigGlobalVariableIdentifier()

    # Is a config item but doesn't start with 'app.'
    assert global_variable_owner.is_global_variable('auth.baz') is False
