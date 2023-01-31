# Buck is a tox plugin to provide centralised tox.ini envs.
#
# Copyright (C) 2023 OpenStack charmers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import configparser
import importlib
import sys
from unittest import mock
from dataclasses import dataclass
from typing import Any, Dict
from types import ModuleType

from ..utils import ModuleMockerTestCase

# unit under test is dynamically loaded in the test as it pulls in the 'tox'
# module which has to be mocked as a module.


TEST_BUCK_CONFIG1 = dict(
    lookup="category",
    category="string:this",
    config_module="a.config.module",
)

TEST_BUCK_CONFIG2 = dict(
    lookup="charm",
    charm="string:that",
    config_module="a.config.module",
)


TESTENV = dict(
    env_name='testenv',
    basepython='python3',
    passenv=('HOME', 'https', 'http', 'no_proxy', 'TEST_*'),
    deps=('dep1', 'dep2')
)

TESTENV_PY3 = dict(
    env_name='testenv:py3',
    commands='run-the-test'  # deliberately not a list of strings.
)


class TestPluginHook4(ModuleMockerTestCase):

    SAVE_MODULES = (
        'tox.config.cli.parser',
        'tox.config.sets',
        'tox.execute',
        'tox.session.state',
        'tox.tox_env.api',
        'tox.tox_env.register',
        'buck.defaults.buckini',
    )

    def setUp(self):
        super().setUp()
        self.tox_hooks_4: ModuleType = importlib.import_module(
            'buck.tox_hooks.tox_hooks_4')

    def tearDown(self):
        self.tox_hooks_4 = None  # type:ignore
        del sys.modules['buck.tox_hooks.tox_hooks_4']
        super().tearDown()

    def test_tox_add_core_config_default(self):
        mock_state = mock.MagicMock()
        mock_parser = mock.Mock()
        
        def items_fail(section):
            raise configparser.NoSectionError(section)

        mock_parser.items.side_effect = items_fail

        mock_state.conf._src._parser = mock_parser
        self.patch_object(self.tox_hooks_4,
                          'use_buck_config',
                          return_value=(dict(category='this'),
                                        [TESTENV, TESTENV_PY3]))
        self.patch_object(self.tox_hooks_4,
                          '_transform_env_to_kv',
                          side_effect=lambda _, x: x)
        self._saved_modules['buck.defaults.buckini'].mock.buck_ini_kv = \
            TEST_BUCK_CONFIG1

        self.tox_hooks_4.tox_add_core_config(None, mock_state)

        mock_parser.items.assert_called_once_with('buck')
        self.use_buck_config.assert_called_once_with(
            list(TEST_BUCK_CONFIG1.items()))
        self._transform_env_to_kv.assert_has_calls([
            mock.call(dict(category='this'), TESTENV),
            mock.call(dict(category='this'), TESTENV_PY3)])
        mock_parser.add_section.assert_has_calls([
            mock.call('testenv'),
            mock.call('testenv:py3')])
        mock_parser.set.assert_has_calls([
            mock.call('testenv', 'basepython', 'python3'),
            mock.call('testenv', 'passenv',
                 ('HOME', 'https', 'http', 'no_proxy', 'TEST_*')),
            mock.call('testenv', 'deps', ('dep1', 'dep2')),
            mock.call('testenv:py3', 'commands', 'run-the-test')])

    def test_tox_add_core_config_supply_config(self):
        mock_state = mock.MagicMock()
        mock_parser = mock.Mock()
        
        mock_parser.items.return_value = list(TEST_BUCK_CONFIG2.items())

        mock_state.conf._src._parser = mock_parser
        self.patch_object(self.tox_hooks_4,
                          'use_buck_config',
                          return_value=(dict(category='this'),
                                        [TESTENV, TESTENV_PY3]))
        self.patch_object(self.tox_hooks_4,
                          '_transform_env_to_kv',
                          side_effect=lambda _, x: x)

        self.tox_hooks_4.tox_add_core_config(None, mock_state)

        mock_parser.items.assert_called_once_with('buck')
        self.use_buck_config.assert_called_once_with(
            list(TEST_BUCK_CONFIG2.items()))
        self._transform_env_to_kv.assert_has_calls([
            mock.call(dict(category='this'), TESTENV),
            mock.call(dict(category='this'), TESTENV_PY3)])
        mock_parser.add_section.assert_has_calls([
            mock.call('testenv'),
            mock.call('testenv:py3')])
        mock_parser.set.assert_has_calls([
            mock.call('testenv', 'basepython', 'python3'),
            mock.call('testenv', 'passenv',
                 ('HOME', 'https', 'http', 'no_proxy', 'TEST_*')),
            mock.call('testenv', 'deps', ('dep1', 'dep2')),
            mock.call('testenv:py3', 'commands', 'run-the-test')])

