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
import sys
from unittest import mock
from types import ModuleType

from ..utils import ModuleMockerTestCase

# unit under test is dynamically loaded in the test as it pulls in the 'tox'
# module which has to be mocked as a module.


TEST_BUCK_CONFIG = dict(
    lookup="category",
    category="string:this",
    config_module="a.confige.module",
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


class TestPluginHook(ModuleMockerTestCase):

    SAVE_MODULES = (
        'tox',
        'tox.config',
    )

    def setUp(self):
        super().setUp()
        self.tox_hooks_3: ModuleType = importlib.import_module(
            'buck.tox_hooks.tox_hooks_3')

    def tearDown(self):
        self.tox_hooks_3 = None  # type:ignore
        del sys.modules['buck.tox_hooks.tox_hooks_3']
        super().tearDown()

    def test_tox_configure(self):
        mock_config = mock.MagicMock()
        mock_config.toxinipath.basename = 'setup.cfg'
        mock_config.envconfigs = {}
        mock_config.envlist = ['hello', 'python', 'build']
        mock_config.envlist_explicit = []
        self.patch_object(self.tox_hooks_3,
                          'get_buck_config',
                          return_value=TEST_BUCK_CONFIG.copy())
        self.patch_object(self.tox_hooks_3,
                          'use_buck_config',
                          return_value=(dict(category='this'),
                                        [TESTENV, TESTENV_PY3]))
        mock_reader = mock.Mock()
        self.patch_object(self.tox_hooks_3,
                          'get_reader',
                          return_value=mock_reader)
        mock_testenv_configs = [mock.Mock(), mock.Mock()]
        self.patch_object(self.tox_hooks_3,
                          'make_tox3_env',
                          side_effect=mock_testenv_configs)

        # run the function under test:
        self.tox_hooks_3.tox_configure(mock_config)

        # assert that the right things were called.
        self.get_buck_config.assert_called_once_with(mock_config)
        self.use_buck_config.assert_called_once_with(TEST_BUCK_CONFIG)
        self.make_tox3_env.assert_has_calls([
            mock.call(mock_reader, mock.ANY, dict(category='this'),
                      mock_config, TESTENV),
            mock.call(mock_reader, mock.ANY, dict(category='this'),
                      mock_config, TESTENV_PY3)])
        self.assertEqual(mock_config.envconfigs['testenv'],
                         mock_testenv_configs[0])
        self.assertEqual(mock_config.envconfigs['py3'],
                         mock_testenv_configs[1])
        self.assertEqual(sorted(mock_config.envlist),
                         ['build', 'hello', 'py3', 'python', 'testenv'])
        self.assertEqual(sorted(mock_config.envlist_default),
                         ['hello', 'py3', 'testenv'])

    def test_get_buck_config_default(self):
        mock_config = mock.MagicMock()
        mock_config._cfg.sections = {}
        from buck.defaults.buckini import buck_ini_kv
        self.assertEqual(self.tox_hooks_3.get_buck_config(mock_config),
                         list(buck_ini_kv.items()))

    def test_get_buck_config_defined(self):
        mock_config = mock.MagicMock()
        mock_config._cfg.sections = dict(
            buck=(dict(
                lookup='category',
                category='string:this',
                config_module='some.module')))
        self.assertEqual(self.tox_hooks_3.get_buck_config(mock_config),
                         [('lookup', 'category'),
                          ('category', 'string:this'),
                          ('config_module', 'some.module')])

    def test_get_reader(self):
        mock_config = mock.MagicMock()
        mock_config.toxworkdir = 'a-dir'
        mock_config.toxinidir = 'some-tox-ini'
        mock_config.homedir = 'a-home-dir'
        mock_config._cfg = mock.Mock()
        reader_sentinel = mock.Mock()
        reader_sentinel.getpath.side_effect = ['path1', 'path2']
        self.patch_object(self.tox_hooks_3, 'SectionReader')
        print(type(self.SectionReader), self.SectionReader)
        self.SectionReader.return_value = reader_sentinel

        reader = self.tox_hooks_3.get_reader(
            mock_config, 'a-section', prefix='a-prefix')

        # verify it did the right things
        self.assertEqual(reader, reader_sentinel)
        self.SectionReader.assert_called_once_with(
            'a-section', mock_config._cfg, prefix='a-prefix')
        reader.getpath.assert_has_calls([
            mock.call("distdir", 'a-dir/dist'),
            mock.call("distshare", "a-home-dir/.tox/distshare")])
        reader.addsubstitutions.assert_has_calls([
            mock.call(toxinidir='some-tox-ini',
                      homedir='a-home-dir',
                      toxworkdir='a-dir'),
            mock.call(distdir='path1'),
            mock.call(distshare='path2')])

    def test_make_tox3_env(self):
        mock_config = mock.MagicMock()
        mock_reader = mock.Mock()
        mock_resolver = mock.Mock()
        subs = {'this': 'that'}
        env = dict(env_name='some-env')
        mock_make_envconfig = mock.Mock()
        self._saved_modules['tox.config'].mock.ParseIni.make_envconfig = \
            mock_make_envconfig
        mock_testenv = mock.MagicMock()
        mock_make_envconfig.return_value = mock_testenv
        mock_DepOption = mock.Mock()
        self._saved_modules['tox.config'].mock.DepOption.return_value = \
            mock_DepOption
        mock_DepOption.postprocess.side_effect = \
            lambda _, x: [f"{_x}-done" for _x in x]

        resolver_calls = []
        resolver_returns = [
            True,  # skipdist
            False,  # skip_instal
            "a-description",
            ['dep1', 'dep2'],
            'python3',  # basepython
            ['command1', 'command2'],
            [],  # set_env
            ['x=y'],  # setenv
            [],  # pass_env
            ['HOME'],  # passenv
            ['thing']  # allowlist_externals
        ]
        resolver_next = 0

        def mock_resolver(env, key, return_type, visited_envs=None):
            nonlocal resolver_calls, resolver_returns, resolver_next
            resolver_calls.append(
                dict(env=env, key=key, return_type=return_type,
                     visited_envs=visited_envs))
            index = resolver_next
            resolver_next += 1
            return resolver_returns[index]

        self.patch_object(self.tox_hooks_3, 'interpolate_value',
                          side_effect=['dep1', 'dep2',
                                       'command1', 'command2',
                                       'y',  # setenv
                                       ])

        mock_testenv.deps = ['existing']
        mock_testenv.setenv = {}
        mock_testenv.passenv = set()
        mock_testenv.allowlist_externals = []
        # this trick ensures that hasattr(..., x) returns False
        hasattr(mock_testenv, 'whitelist_externals')
        del mock_testenv.whitelist_externals

        # now make the env.
        testenv_returned = self.tox_hooks_3.make_tox3_env(
            mock_reader, mock_resolver, subs, mock_config, env)

        # now verify that everything was called correctly
        self.assertEqual(testenv_returned, mock_testenv)
        self.assertEqual(testenv_returned.skipsdist, True)
        self.assertEqual(testenv_returned.skip_install, False)
        self.assertEqual(testenv_returned.description, 'a-description')
        self.assertEqual(testenv_returned.deps,
                         ['existing', 'dep1-done', 'dep2-done'])
        self.assertEqual(testenv_returned.basepython, 'python3')
        self.assertEqual(testenv_returned.commands,
                         [['command1'], ['command2']])
        self.assertEqual(testenv_returned.setenv,
                         dict(x='y'))
        self.assertEqual(testenv_returned.passenv, set(['HOME']))
        self.assertEqual(testenv_returned.allowlist_externals,
                         ['thing'])

    def test_interpolate_value(self):
        mock_config = mock.MagicMock()
        mock_config.option.args = ['a', 'b', 'c']
        mock_config.toxinidir = 'ini-dir'
        mock_config.toxworkdir = 'work-dir'
        mock_config.homedir = 'home-dir'
        mock_config.distshare = 'dist'

        subs = dict(this='that', one='two')
        interpolate = self.tox_hooks_3.interpolate_value

        self.assertEqual(
            interpolate(mock_config, subs, "Some {posargs}"),
            "Some a b c")
        self.assertEqual(
            interpolate(mock_config, subs, "The {toxinidir}"),
            "The ini-dir")
        self.assertEqual(
            interpolate(mock_config, subs, "The {toxworkdir}"),
            "The work-dir")
        self.assertEqual(
            interpolate(mock_config, subs, "The {homedir} in {distshare}"),
            "The home-dir in dist")
        self.assertEqual(
            interpolate(mock_config, subs,
                        "The {this} in {distshare} and {one}"),
            "The that in dist and two")
