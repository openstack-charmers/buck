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

from dataclasses import dataclass
from typing import Union, Iterable, Tuple, cast, Dict

from .utils import BaseTestCase

# unit under test
import buck.config as config


class TestConfig(BaseTestCase):

    def setUp(self):
        super().setUp()
        config.envs = None
        config.selectors = None
        config.mappings = None

    def test_default(self):
        a_default = config.default
        self.assertEqual(a_default, config.default)
        self.assertEqual(a_default, ':default:')
        self.assertTrue(a_default == ':default:')
        self.assertEqual(str(a_default), ':default:')

    def test_get_envs_singleton(self):
        self.assertEqual(config.get_envs_singleton(), {})
        config.envs = dict(a=1, b=2)
        self.assertEqual(config.get_envs_singleton(), dict(a=1, b=2))

    def test_get_selectors_singleton(self):
        self.assertEqual(config.get_selectors_singleton(), {})
        config.selectors = dict(a=1, b=2)
        self.assertEqual(config.get_selectors_singleton(), dict(a=1, b=2))

    def test_get_mappings_singleton(self):
        self.assertEqual(config.get_mappings_singleton(), {})
        config.mappings = dict(a=1, b=2)
        self.assertEqual(config.get_mappings_singleton(), dict(a=1, b=2))

    def test_validate_env_vars(self):

        @dataclass
        class TestItem:
            item: Union[str, Iterable[Union[str, bool]], bool]
            match: Union[str, None]
            notfail: bool

        # test each item individually
        string_pass = TestItem('pass', 'pass', True)
        string_fail = TestItem('pass', None, False)
        bool_fail = TestItem(False, None, False)
        bool_pass = TestItem(True, 'True', True)
        iterable_string_pass_comma = TestItem(
            ['pass', 'me'], "pass, me", True)
        iterable_string_pass_newline = TestItem(
            ['pass', 'me'], "pass\nme", True)
        iterable_string_fail = TestItem(['pass', 'me'], None, False)
        iterable_bool_fail = TestItem([False, False], None, False)

        # sets of tests
        string: Tuple[TestItem, ...] = (
            string_pass,
            bool_fail,
            iterable_string_fail,
            iterable_bool_fail)
        bool_set: Tuple[TestItem, ...] = (
            bool_pass,
            string_fail,
            iterable_string_fail,
            iterable_bool_fail)
        iterable_string_comma: Tuple[TestItem, ...] = (
            string_pass,
            iterable_string_pass_comma,
            iterable_bool_fail,
            bool_fail)
        iterable_string_newline: Tuple[TestItem, ...] = (
            string_pass,
            iterable_string_pass_newline,
            iterable_bool_fail,
            bool_fail)

        test_items = dict(
            env_name=string,
            description=string,
            setenv=iterable_string_comma,
            commands=iterable_string_newline,
            allowlist_externals=iterable_string_comma,
            passenv=iterable_string_comma,
            deps=iterable_string_newline,
            basepython=string,
            platform=string,
            parallel_show_output=bool_set,
            recreate=bool_set,
            skip_install=bool_set,
            labels=iterable_string_comma,
        )

        # validate that the keys do work and validate appropriately
        for name, specs in test_items.items():
            for spec in specs:
                vars = {}
                matches = {}
                vars[name] = spec.item
                matches[name] = spec.match
                if spec.notfail:
                    self.assertEqual(config.validate_env_vars(**vars),
                                     matches)
                else:
                    with self.assertRaises(TypeError):
                        config.validate_env_vars(**vars)

        # check for key error for unknown data
        with self.assertRaises(KeyError):
            config.validate_env_vars(unknown=3)

        # Finally, check that it can handle multiple keys
        keys = ('env_name', 'commands', 'skip_install')
        # find a passing version item.
        test_set = [[i for i in test_items[key] if i.notfail][0]
                    for key in keys]
        test_values = [v.item for v in test_set]
        test_matches = [v.match for v in test_set]
        data = {k: v for k, v in zip(keys, test_values)}
        match = {k: v for k, v in zip(keys, test_matches)}
        self.assertEqual(config.validate_env_vars(**data), match)

    def test_register_env_section(self):
        data1 = dict(
            env_name='a',
            basepython='python3',
            skip_install=True,
        )
        data2 = dict(
            env_name='b',
            basepython='python3',
            commands="this command",
        )
        bad_data = dict(
            basepython='python3',
            commands="this command",
        )
        # self.patch_object(config, 'validate_env_vars')
        config.register_env_section('a', **data1)
        self.assertIn('a', cast(dict, config.envs).keys())
        config.register_env_section('b', **data2)
        self.assertIn('a', cast(dict, config.envs).keys())
        self.assertIn('b', cast(dict, config.envs).keys())
        with self.assertRaises(config.DuplicateKeyError):
            config.register_env_section('a', **data1)
        with self.assertRaises(AssertionError):
            config.register_env_section('c', **bad_data)

    def test_selectormatcher_class(self):
        a = config.SelectorMatcher('a', 'this', 'one', 'is', 'match')
        self.assertTrue(a('a', 'this'))
        self.assertTrue(a('a', 'is'))
        self.assertFalse(a('a', 'no'))
        self.assertFalse(a('b', 'this'))

        with self.assertRaises(config.ParameterError):
            config.SelectorMatcher('b', 'one', config.default)

        b = config.SelectorMatcher('b', config.default)
        self.assertTrue(b.is_default)
        self.assertTrue(b('b', config.default))
        self.assertTrue(b('b', config.default._name))
        self.assertTrue(b('b', 'any'))

    def test_selector_matcher_factory(self):
        a_factory = config.selector_matcher_factory('a')
        matcher = a_factory('this', 'one', 'is', 'fine')
        self.assertTrue(matcher('a', 'this'))
        self.assertFalse(matcher('b', 'this'))
        self.assertFalse(matcher('a', 'else'))
        self.assertFalse(matcher('b', 'else'))

    def test_register_selector_name(self):
        a = config.register_selector_name('a')
        self.assertIn('a', config.selectors)
        with self.assertRaises(config.DuplicateKeyError):
            config.register_selector_name('a')
        config.register_selector_name('b')
        self.assertIn('a', config.selectors)
        self.assertIn('b', config.selectors)
        matcher = a('this', 'one')
        self.assertTrue(matcher('a', 'this'))
        self.assertFalse(matcher('a', 'else'))

    def test_mapping_class(self):
        a = config.register_selector_name('a')
        matcher = a('this', 'one')
        data1 = dict(
            env_name='a',
            basepython='python3',
            skip_install=True,
        )
        config.register_env_section('an-env', **data1)
        mapping = config.Mapping(
            'a-mapping', [matcher],
            [config.get_envs_singleton()['an-env']])
        self.assertTrue(mapping.match(dict(a='this')))
        self.assertFalse(mapping.match(dict(b='this')))
        self.assertFalse(mapping.match(dict(a='else')))

    def test_register_mapping(self):
        classic_testenv = config.register_env_section(
            name='classic_testenv',
            env_name='testenv',
            skip_install=True,
            setenv=('VIRTUAL_ENV={envdir}',
                    'PYTHONHASHSEED=0',
                    'CHARM_DIR={envdir}'),
            commands='stestr run --slowest {posargs}',
            allowlist_externals=('charmcraft',
                                 '{toxinidir}/rename.sh'),
            basepython="python3",
            passenv=('HOME',
                     'TERM',
                     'CS_*',
                     'OS_*',
                     'TEST_*'),
            deps='-r{toxinidir}/test-requirements.txt',
        )
        classic_build = config.register_env_section(
            name='classic_build',
            env_name="testenv:build",
            basepython="python3",
            # charmcraft clean is done to ensure that
            # `tox -e build` always performs a clean, repeatable build.
            # For faster rebuilds during development,
            # directly run `charmcraft -v pack && ./rename.sh`.
            commands=('charmcraft clean',
                      'charmcraft -v pack',
                      '{toxinidir}/rename.sh',
                      'charmcraft clean'),
            deps="a dep",
        )
        category = config.register_selector_name('category')
        openstack_category = category('openstack')
        config.register_mapping(
            name="any-classic-master",
            selectors=(openstack_category, ),
            env_list=(classic_testenv,
                      classic_build, ))

        self.assertIn('any-classic-master', cast(dict, config.mappings).keys())
        mapping = config.get_mappings_singleton()['any-classic-master']
        envs = config.get_envs_singleton()
        self.assertEqual(mapping.name, 'any-classic-master')
        self.assertEqual(mapping.selectors, [openstack_category])
        self.assertEqual(mapping.envs, [envs[classic_testenv],
                                        envs[classic_build]])
        # now test for failures
        with self.assertRaises(config.ParameterError):
            config.register_mapping(
                name='bad-one',
                selectors=[],
                env_list=(classic_testenv, classic_build, ))
        with self.assertRaises(config.ParameterError):
            config.register_mapping(
                name='bad-one',
                selectors=[openstack_category],
                env_list=[])
        dup_category = category('openstack')
        with self.assertRaises(config.ParameterError):
            config.register_mapping(
                name="bad-one",
                selectors=(openstack_category, dup_category),
                env_list=(classic_testenv,
                          classic_build, ))
        with self.assertRaises(config.ParameterError):
            config.register_mapping(
                name="bad-one",
                selectors=(openstack_category, ),
                env_list=(classic_testenv,
                          classic_build,
                          classic_testenv,))
        with self.assertRaises(config.ParameterError):
            config.register_mapping(
                name="bad-one",
                selectors=(openstack_category, ),
                env_list=("unknown", ))
        # and finally a duplicate mapping that works.
        with self.assertRaises(config.DuplicateKeyError):
            config.register_mapping(
                name="any-classic-master",
                selectors=(openstack_category, ),
                env_list=(classic_testenv,
                          classic_build, ))

    def test_resolve_envs_by_selectors(self):
        envs = {}
        # create sets of envs
        for env_num in range(1, 7):
            envs[f"env{env_num}_1"] = config.register_env_section(
                name=f'env{env_num}_1',
                env_name=f'testenv_{env_num}',
                basepython="python3",
            )
            envs[f"env{env_num}_2"] = config.register_env_section(
                name=f'env{env_num}_2',
                env_name=f'testenv:build_{env_num}',
                passenv=('HOME', ),
                commands="a-command",
                deps="a dep",
            )

        category = config.register_selector_name('category')
        charm = config.register_selector_name('charm')
        branch = config.register_selector_name('branch')

        any_cat = category(config.default)
        cat1 = category('cat1')
        cat2 = category('cat2')

        any_charm = charm(config.default)
        special_charm = charm('special-charm')

        main_branch = branch('main')

        # register increasingly specific selectors for env lists
        # most general, but still matching cat1 or cat2
        config.register_mapping(
            name="cat1",
            selectors=(cat1, ),
            env_list=(envs['env1_1'], envs['env1_2']))

        config.register_mapping(
            name="cat2",
            selectors=(cat2, ),
            env_list=(envs['env2_1'], envs['env2_2']))

        # any category, special charm
        config.register_mapping(
            name="special-charm",
            selectors=(any_cat, special_charm),
            env_list=(envs['env3_1'], envs['env3_2']))

        # cat1 category, special charm
        config.register_mapping(
            name="cat1-special-charm",
            selectors=(cat1, special_charm),
            env_list=(envs['env4_1'], envs['env4_2']))

        # any category, any charm, main branch
        config.register_mapping(
            name="main-branch",
            selectors=(main_branch, any_charm, any_cat),
            env_list=(envs['env5_1'], envs['env5_2']))

        config.register_mapping(
            name="very-specific",
            selectors=(cat1, main_branch, special_charm, ),
            env_list=(envs['env6_1'], envs['env6_2']))

        # now test that we get the right envs back.
        # start with no selectors == no envs == error
        with self.assertRaises(config.SelectionError):
            config.resolve_envs_by_selectors({})

        def _validate(criteria: Dict[str, str], env_num: int):
            envs = config.resolve_envs_by_selectors(criteria)
            env_names = [e['env_name'] for e in envs]
            self.assertEqual(
                env_names, [f'testenv_{env_num}', f'testenv:build_{env_num}'])

        # getting less specific
        _validate(
            dict(category="cat1", branch="main", charm="special-charm"), 6)
        _validate(dict(branch="main"), 5)
        _validate(dict(category="cat1", charm="special-charm"), 4)
        _validate(dict(category="cat2", charm="special-charm"), 3)
        _validate(dict(category="cat2"), 2)
        _validate(dict(category="cat1"), 1)

    def test_use_buck_config(self):
        self.patch('importlib.import_module', name='mock_import_module')

        def custom_function() -> str:
            return 'thing'

        self.patch_object(config, 'resolve_function',
                          return_value=custom_function)
        self.patch_object(config, 'resolve_envs_by_selectors',
                          return_value="resolved_envs")

        resolved_selectors, envs = config.use_buck_config([
            ('lookup', 'category branch'),
            ('category', 'string:hello'),
            ('branch', 'function:a.custom.module.call_me'),
            ('config_module', 'a.custom.config.module'),
        ])
        self.assertEqual(envs, 'resolved_envs')
        self.mock_import_module.assert_called_once_with(
            'a.custom.config.module')

        self.assertEqual(resolved_selectors,
                         {'category': 'hello', 'branch': 'thing'})

    def test_resolve_function(self):
        self.patch('importlib.import_module', name='mock_import_module')

        class FakeModule:

            @staticmethod
            def the_function():
                pass

        self.mock_import_module.return_value = FakeModule

        self.assertEqual(
            config.resolve_function("an.interesting.module.the_function"),
            FakeModule.the_function)
        self.mock_import_module.assert_called_once_with(
            "an.interesting.module")

    def test_do_substitutions(self):
        subs = {
            '{this}': 'one',
            '{that}': 'two',
        }
        self.assertEqual(config.do_substitutions(subs, True), True)
        self.assertEqual(config.do_substitutions(subs, False), False)
        self.assertEqual(config.do_substitutions(subs, "any"), "any")
        self.assertEqual(
            config.do_substitutions(subs, "any {this}"), "any one")
        self.assertEqual(
            config.do_substitutions(subs, "{this} {that}"), "one two")
        self.assertEqual(
            config.do_substitutions(subs, ["{this}", "and {that}"]),
            ["one", "and two"])

    def test_make_keys_variable_form(self):
        subs = {
            'this': 'one',
            'that': 'two',
        }
        self.assertEqual(config.make_keys_variable_form(subs),
                         {'{this}': 'one', '{that}': 'two'})

    def test_env_resolver(self):
        testenv = cast(config.Env, dict(
            env_name='testenv',
            skip_install=True,
            basepython="python3",
            setenv=('VIRTUAL_ENV={envdir}',
                    'CHARM_DIR={envdir}'),
            commands='stestr run --slowest {posargs}',
            allowlist_externals=('charmcraft',
                                 '{toxinidir}/rename.sh'),
            passenv=('HOME',
                     'TEST_*'),
            deps='-r{toxinidir}/test-requirements.txt',
        ))
        build = cast(config.Env, dict(
            env_name="testenv:build",
            passenv=('{[testenv]passenv}',
                     'EXTRA'),
            commands=('charmcraft clean',
                      'charmcraft -v pack'),
            deps="a dep",
        ))
        env3 = cast(config.Env, dict(
            env_name="testenv:py3",
            commands="stestr",
        ))
        envs = [testenv, build, env3]

        # verify things
        self.assertEqual(
            config.env_resolver(envs, testenv, 'skip_install', bool), True)
        self.assertEqual(
            config.env_resolver(envs, testenv, 'basepython', str), 'python3')
        self.assertEqual(
            config.env_resolver(envs, testenv, 'commands', list),
            ['stestr run --slowest {posargs}'])
        self.assertEqual(
            config.env_resolver(envs, build, 'skip_install', bool), True)
        self.assertEqual(
            config.env_resolver(envs, env3, 'skip_install', bool), True)
        # verify overrides work.
        self.assertEqual(
            config.env_resolver(envs, testenv, 'deps', list),
            ['-r{toxinidir}/test-requirements.txt'])
        self.assertEqual(
            config.env_resolver(envs, build, 'deps', list), ['a dep'])
        # verify intepolation works for inherited vars
        self.assertEqual(
            config.env_resolver(envs, testenv, 'passenv', list),
            ['HOME', 'TEST_*'])
        self.assertEqual(
            config.env_resolver(envs, build, 'passenv', list),
            ['HOME', 'TEST_*', 'EXTRA'])

    def test_env_resolver_circular(self):
        testenv = cast(config.Env, dict(
            env_name='testenv',
            basepython="python3",
            setenv=('VIRTUAL_ENV={envdir}',
                    'CHARM_DIR={envdir}'),
        ))
        build = cast(config.Env, dict(
            env_name="testenv:build",
            passenv=('{[testenv:py3]passenv}',
                     'EXTRA'),
            commands=('charmcraft clean',
                      'charmcraft -v pack'),
            deps="a dep",
        ))
        env3 = cast(config.Env, dict(
            env_name="testenv:py3",
            commands="stestr",
            passenv=('{[testenv:build]passenv}',
                     'EXTRA'),
        ))
        envs = [testenv, build, env3]
        with self.assertRaises(config.ParameterError):
            config.env_resolver(
                envs, build, 'passenv', list)

        env4 = cast(config.Env, dict(
            env_name="testenv:py3",
            commands="stestr",
            passenv=('{[testenv:py3]passenv}',
                     'EXTRA'),
        ))
        envs = [env4]
        with self.assertRaises(config.ParameterError):
            config.env_resolver(
                envs, env4, 'passenv', list)

    def test_env_resolver_bad_list(self):
        testenv = cast(config.Env, dict(
            env_name='testenv',
            basepython="python3",
            setenv=('VIRTUAL_ENV={envdir}',
                    'CHARM_DIR={envdir}'),
        ))
        with self.assertRaises(config.ParameterError):
            config.env_resolver(
                [testenv], testenv, 'setenv', str)

    def test_env_resolver_no_inherited_value(self):
        testenv = cast(config.Env, dict(
            env_name='testenv',
            basepython="python3",
            setenv=('VIRTUAL_ENV={envdir}',
                    'CHARM_DIR={envdir}'),
        ))
        build = cast(config.Env, dict(
            env_name='testenv:build',
            basepython="python3",
            passenv=('{[testenv]passenv}'),
        ))
        with self.assertRaises(config.ParameterError):
            config.env_resolver(
                [testenv, build], build, 'passenv', str)

    def test_env_resolver_unknown(self):
        testenv = cast(config.Env, dict(
            env_name='testenv',
            basepython="python3",
            setenv=('VIRTUAL_ENV={envdir}',
                    'CHARM_DIR={envdir}'),
        ))
        self.assertIsNone(config.env_resolver(
            [testenv], testenv, 'skip_install', bool), None)

    def test_env_resolver_missing_env_name(self):
        testenv = cast(config.Env, dict(
            env_name='testenv',
            basepython="python3",
            setenv=('VIRTUAL_ENV={envdir}',
                    'CHARM_DIR={envdir}'),
        ))
        build = cast(config.Env, dict(
            env_name='testenv:build',
            basepython="python3",
            setenv=('{[testenv:py3]setenv}'),
        ))
        with self.assertRaises(config.ParameterError):
            config.env_resolver(
                [testenv, build], build, 'setenv', str)
