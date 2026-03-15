import pytest
from unittest.mock import patch
from app.utility.base_world import BaseWorld


class TestShlexSplit:
    def test_simple_command(self):
        params = {'type': 'installed_program', 'command': 'python3 --version', 'version': '3.0'}
        with patch('subprocess.check_output', return_value=b'Python 3.12.0') as mock:
            result = BaseWorld.check_requirement(params)
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args == ['python3', '--version']
            assert result is True

    def test_command_with_quotes(self):
        params = {'type': 'installed_program', 'command': 'echo "hello world"', 'version': '0.0.0'}
        with patch('subprocess.check_output', return_value=b'1.0.0') as mock:
            BaseWorld.check_requirement(params)
            args = mock.call_args[0][0]
            assert args == ['echo', 'hello world']

    def test_command_with_spaces_in_path(self):
        params = {'type': 'installed_program', 'command': "'/path/to/my program' --version", 'version': '1.0'}
        with patch('subprocess.check_output', return_value=b'1.5.0') as mock:
            BaseWorld.check_requirement(params)
            args = mock.call_args[0][0]
            assert args == ['/path/to/my program', '--version']
