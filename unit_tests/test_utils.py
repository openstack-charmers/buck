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

import importlib
import os
import sys
from typing import List
from types import ModuleType
from unittest import mock
import yaml

from .utils import ModuleMockerTestCase, patch_open

# unit under test is dynamically loaded so as to be able to patch out @cache


class TestUtils(ModuleMockerTestCase):

    SAVE_MODULES = ['pathlib']

    def setUp(self):
        super().setUp()
        self.patch('functools.cache', name='_functools_cache',
                   new=lambda x: x)
        self.buck_utils = self._reload_module('buck.utils')

    @staticmethod
    def _reload_module(module: str) -> ModuleType:
        """Reload the module if it's loaded, otherwise just load it."""
        try:
            del sys.modules[module]
        except KeyError:
            pass
        return importlib.import_module(module)

    def test_read_gitreview_doesnt_exist(self):
        self.patch('os.getcwd', name='_mock_getcwd', return_value='/some/path')
        self.patch('os.path.isfile', name='_mock_isfile', return_value=False)
        self.assertIsNone(self.buck_utils.read_gitreview())

    def test_read_gitreview_succeeds(self):
        self.patch('os.getcwd', name='_mock_getcwd', return_value='/some/path')
        self.patch('os.path.isfile', name='_mock_isfile', return_value=True)
        mock_config = mock.Mock()
        self.patch('configparser.ConfigParser', name='_mock_configparser',
                   return_value=mock_config)
        mock_config.read.return_value = "the config"
        self.assertEqual(self.buck_utils.read_gitreview(), mock_config)
        mock_config.read.assert_called_once_with('/some/path/.gitreview')

    def test_read_metadata_file(self):
        self.patch('yaml.load', name='mock_yaml_load',
                   return_value="some contents")
        with patch_open() as (mock_open, mock_file):
            self.assertEqual(self.buck_utils.read_metadata_file(),
                             "some contents")
            mock_open.assert_called_once_with('metadata.yaml', 'r')
            self.mock_yaml_load.assert_called_once_with(
                mock_file, Loader=yaml.SafeLoader)

    def test_get_gitreview_line(self):
        self.patch_object(self.buck_utils, 'read_gitreview',
                          return_value={
                              'gerrit': {
                                  'some-line': 'has a value',
                                  'other-line': 'this line',
                              },
                          })
        self.assertIsNone(self.buck_utils.get_gitreview_line('no-line'))
        self.assertEqual(self.buck_utils.get_gitreview_line('some-line'),
                         'has a value')

    def test_is_k8s_charm(self):
        self.patch_object(self.buck_utils, 'read_metadata_file',
                          return_value={
                              'containers': 'str',
                          })
        self.assertTrue(self.buck_utils.is_k8s_charm())
        self.read_metadata_file.return_value = {'no-containers': 'str'}
        self.assertFalse(self.buck_utils.is_k8s_charm())
        self.read_metadata_file.return_value = None
        self.assertFalse(self.buck_utils.is_k8s_charm())

    def test_get_charm_type(self):
        class FakePosixPath:

            def __init__(self):
                self.path: str = ''
                self.index: int = 0
                self.return_values = []
                self.calls: List[str] = []

            def __call__(self, path: str) -> 'FakePosixPath':
                self.calls.append(path)
                self.path = path
                return self

            def __truediv__(self, other: str) -> 'FakePosixPath':
                self.path = os.path.join(self.path, other)
                self.calls.append(other)
                return self

            def exists(self) -> bool:
                value = self.return_values[self.index]
                self.index += 1
                return value

            def reset(self) -> None:
                self.path = ''
                self.index = 0
                self.calls = []

        self.patch_object(self.buck_utils, 'is_k8s_charm', return_value=True)
        self.assertEqual(self.buck_utils.get_charm_type(), self.buck_utils.K8S)
        self.is_k8s_charm.return_value = False
        mock_posixpath = FakePosixPath()
        self._saved_modules['pathlib'].mock.PosixPath = mock_posixpath
        mock_posixpath.return_values = [True]  # REACTIVE
        self.assertEqual(self.buck_utils.get_charm_type(),
                         self.buck_utils.REACTIVE)
        self.assertEqual(mock_posixpath.path, './src/layer.yaml')
        self.assertEqual(mock_posixpath.calls, ['.', 'src', 'layer.yaml'])
        mock_posixpath.reset()
        mock_posixpath.return_values = [False, True]  # OPS
        self.assertEqual(self.buck_utils.get_charm_type(),
                         self.buck_utils.OPS)
        self.assertEqual(mock_posixpath.path, './src/charm.py')
        self.assertEqual(mock_posixpath.calls, ['.', 'src', 'layer.yaml',
                                                '.', 'src', 'charm.py'])
        mock_posixpath.reset()
        mock_posixpath.return_values = [False, False, True]  # CLASSIC
        self.assertEqual(self.buck_utils.get_charm_type(),
                         self.buck_utils.CLASSIC)
        self.assertEqual(mock_posixpath.path, './charm-helpers-hooks.yaml')
        self.assertEqual(mock_posixpath.calls,
                         ['.', 'src', 'layer.yaml',
                          '.', 'src', 'charm.py',
                          '.', 'charm-helpers-hooks.yaml'])
        mock_posixpath.reset()
        # mock_filename.exists.side_effect = [False, False, False] # UNKNOWN
        mock_posixpath.return_values = [False, False, False]  # UNKNOWN
        self.assertEqual(self.buck_utils.get_charm_type(),
                         self.buck_utils.UNKNOWN)

    def test_get_branch_name(self):
        self.patch_object(self.buck_utils, 'get_gitreview_line')
        self.get_gitreview_line.return_value = "a-branch"
        self.assertEqual(self.buck_utils.get_branch_name(), 'a-branch')
        self.get_gitreview_line.return_value = None
        self.assertEqual(self.buck_utils.get_branch_name(),
                         self.buck_utils.DEFAULT_BRANCH)

    def test_get_charm_name(self):
        self.patch_object(self.buck_utils, 'get_gitreview_line')
        self.get_gitreview_line.return_value = None
        with self.assertRaises(RuntimeError):
            self.buck_utils.get_charm_name()
        self.get_gitreview_line.return_value = 'openstack/charm-nova-compute'
        self.assertEqual(self.buck_utils.get_charm_name(), 'nova-compute')
