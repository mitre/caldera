import pytest
import os
import yaml

from datetime import datetime, timezone
from unittest import mock
from app.utility.base_world import BaseWorld


class TestBaseWorld:

    default_config = dict(name='main', config={'app.contact.http': '0.0.0.0', 'plugins': ['sandcat', 'stockpile']})

    default_yaml = dict(test_dir=1, implant_name='unittesting', test_int=1234)

    @pytest.fixture
    def reset_config(self):
        BaseWorld.apply_config(**self.default_config)
        yield
        BaseWorld._app_configuration = dict()

    @pytest.fixture
    def yaml_file(self, tmpdir):
        f = tmpdir.mkdir('yml').join('test.yml')
        yaml_str = yaml.dump(self.default_yaml)
        f.write(yaml_str)
        assert f.read() == yaml_str
        yield f

    @pytest.fixture
    def text_file(self, tmpdir):
        txt_str = 'Hello world!'
        f = tmpdir.mkdir('txt').join('test.txt')
        f.write(txt_str)
        assert f.read() == txt_str
        yield f

    @pytest.mark.usefixtures('reset_config')
    def test_apply_and_retrieve_config(self):
        new_config = dict(name='newconfig', config={'app.unit.test': 'abcd12345', 'plugins': ['stockpile']})
        BaseWorld.apply_config(**new_config)

        assert BaseWorld.get_config(name='newconfig') == new_config['config']

    @pytest.mark.usefixtures('reset_config')
    def test_get_prop_from_config(self):
        assert BaseWorld.get_config(name='main', prop='app.contact.http') == '0.0.0.0'

    @pytest.mark.usefixtures('reset_config')
    def test_set_prop_from_config(self):
        BaseWorld.set_config(name='main', prop='newprop', value='unittest')
        assert BaseWorld.get_config(name='main', prop='newprop') == 'unittest'

    def test_encode_and_decode_string(self):
        plaintext = 'unit testing string'
        encoded_text = 'dW5pdCB0ZXN0aW5nIHN0cmluZw=='
        encoded_str = BaseWorld.encode_string(plaintext)

        assert encoded_str == encoded_text

        decoded_str = BaseWorld.decode_bytes(encoded_text)
        assert decoded_str == plaintext

    def test_jitter(self):
        fraction = "1/5"
        frac_arr = fraction.split('/')
        jitter = BaseWorld.jitter(fraction)
        assert jitter >= int(frac_arr[0])
        assert jitter <= int(frac_arr[1])

    def test_strip_yml_no_path(self):
        yaml = BaseWorld.strip_yml(None)
        assert yaml == []

    def test_strip_yml(self, yaml_file):
        yaml = BaseWorld.strip_yml(yaml_file)
        assert yaml == [self.default_yaml]

    def test_prepend_to_file(self, text_file):
        line = 'This is appended!'
        BaseWorld.prepend_to_file(text_file, line)
        assert 'This is appended!\nHello world!' == text_file.read()

    def test_get_current_timestamp(self):
        date_format = '%Y-%m-%d %H'
        output = BaseWorld.get_current_timestamp(date_format)
        cur_time = datetime.now(timezone.utc).strftime(date_format)
        assert cur_time == output

    def test_is_not_base64(self):
        assert not BaseWorld.is_base64('not base64')

    def test_is_base64(self):
        b64str = 'aGVsbG8gd29ybGQgZnJvbSB1bml0IHRlc3QgbGFuZAo='
        assert BaseWorld.is_base64(b64str)

    @mock.patch.object(os, 'listdir', return_value=['stockpile', 'testplugin', 'dummy'])
    @mock.patch.object(os.path, 'isdir', return_value=True)
    def test_verify_module(self, mock_isdir, mock_listdir):
        def _mock_isfile(path):
            return path in [
                'plugins/stockpile/app/requirements/test_req.py',
                'plugins/testplugin/app/obfuscators/test_obf.py',
                'app/planners/test_planner.py',
                'app/parsers/test_parser.py',
                'app/learning/learning_parser.py',
            ]

        with mock.patch.object(os.path, 'isfile', side_effect=_mock_isfile):
            BaseWorld.verify_module('plugins.stockpile.app.requirements.test_req', 'requirements')
            BaseWorld.verify_module('plugins.testplugin.app.obfuscators.test_obf', 'obfuscators')
            BaseWorld.verify_module('app.planners.test_planner', 'planners')
            BaseWorld.verify_module('app.parsers.test_parser', 'parsers')
            BaseWorld.verify_module('app.learning.learning_parser', 'parsers', ['app/learning'])

            allowed_paths_str = str([
                'app/parsers/myparser.py',
                'plugins/stockpile/parsers/myparser.py',
                'plugins/testplugin/parsers/myparser.py',
                'plugins/dummy/parsers/myparser.py'
            ])
            expected_err = f'Module data.payloads.myparser does not align with allowed paths for this module type. Allowed paths for this module: {allowed_paths_str}'
            with pytest.raises(ModuleNotFoundError, match=expected_err):
                BaseWorld.verify_module('data.payloads.myparser', 'parsers')
            allowed_paths_str = str([
                'otherdir/myparser.py',
                'app/parsers/myparser.py',
                'plugins/stockpile/parsers/myparser.py',
                'plugins/testplugin/parsers/myparser.py',
                'plugins/dummy/parsers/myparser.py'
            ])
            expected_err = f'Module plugins.dne.myparser does not align with allowed paths for this module type. Allowed paths for this module: {allowed_paths_str}'
            with pytest.raises(ModuleNotFoundError, match=expected_err):
                BaseWorld.verify_module('data.payloads.myparser', 'parsers', ['otherdir'])
            expected_err = 'Module plugins.stockpile.app.obfuscators.dne with path plugins/stockpile/app/obfuscators/dne was not found on disk.'
            with pytest.raises(ModuleNotFoundError, match=expected_err):
                BaseWorld.verify_module('plugins.stockpile.app.obfuscators.dne', 'obfuscators', ['otherdir'])
