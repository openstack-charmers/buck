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


# Configuration of dynamically generating environments for tox 3.x and 4.x
#
# This configuration feeds to the hooks implementation of both tox 3 and tox 4.
# Tox 4 was a complete rewrite from tox 3 and therefore, the internals changed
# completely.  Thus the way a plugin works in tox 3 doesn't work in tox 4.
#
# Thus this configuration data is shared between the two implementations.
#
# NOTE:
#
# This configuration may be broken out into a separate repo to make this plugin
# more general. Please raise an issue if you'd like to use this tox plugin for
# other charms; the configuration is here simply for ease-of-use at present.

# The configuration is hierachical and is selected by 'n' keys.  Buck will read
# the [buck] section from the tox.ini to determine how to lookup the values in
# the config.
#
# The default for openstack charms is:
#
# [buck]
# lookup = category branch charm
# category = string:openstack
# branch = function:buck.select.get_branch_from_gitreview
# charm = function:buck.select.get_charm_from_gitreview
# config_module = buck.config

# This would cause buck to use the key 'openstack' initially, and then refine
# that to looking up the charm and branch from the .gitreview file. The
# functions may return a default value which is then used as the selector.

import pathlib

from buck.config import (
    default, register_env_section, register_selector_name, register_mapping)


from typing import Tuple

###
#
# Handy constants
#
###

GLOBAL_CONFIG: str = (
    "https://raw.githubusercontent.com/openstack-charmers/release-tools"
    "/master/global")
ZOT_CLASSIC_TEST_REQUIREMENTS_TXT: str = (
    f"-r{GLOBAL_CONFIG}/classic-zaza/test-requirements.txt")
ZOT_REACTIVE_TEST_REQUIREMENTS_TXT: str = (
    f"-r{GLOBAL_CONFIG}/source-zaza/src/test-requirements.txt")


###
#
# release-tools/global/classic envs
#
###

classic_testenv = register_env_section(
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


classic_build = register_env_section(
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
    deps=f"{GLOBAL_CONFIG}/classic-zaza/build-requirements.txt",
)


classic_sync_build = register_env_section(
    name='classic_sync_build',
    env_name="testenv:build",
    description=(
        "Build of classic charms including a 'make sync' prior to the "
        "charmcraft build being performed to update the charmhelpers."),
    basepython="python3",
    # charmcraft clean is done to ensure that
    # `tox -e build` always performs a clean, repeatable build.
    # For faster rebuilds during development,
    # directly run `charmcraft -v pack && ./rename.sh`.
    commands=('make sync',
              'charmcraft clean',
              'charmcraft -v pack',
              '{toxinidir}/rename.sh',
              'charmcraft clean'),
    deps=f"{GLOBAL_CONFIG}/classic-zaza/build-requirements.txt",
    allowlist_externals=('{[testenv]allowlist_externals}',
                         'make'),
)


classic_py3 = register_env_section(
    name='classic_py3',
    env_name='testenv:py3',
    basepython='python3',
    deps=('-r{toxinidir}/requirements.txt',
          ZOT_CLASSIC_TEST_REQUIREMENTS_TXT)
)


classic_py3_keystone_test = register_env_section(
    name='classic_py3_keystone_test',
    description="Custom py3 testenv that uses local test-requirements.txt",
    env_name='testenv:py3',
    basepython='python3',
    commands=(
        'make sync',
        'stestr run --slowest {posargs}',
    ),
    deps=('-r{toxinidir}/requirements.txt',
          ZOT_CLASSIC_TEST_REQUIREMENTS_TXT)
)


classic_py310 = register_env_section(
    name='classic_py310',
    env_name='testenv:py310',
    basepython='python3.10',
    deps=('-r{toxinidir}/requirements.txt',
          ZOT_CLASSIC_TEST_REQUIREMENTS_TXT)
)

classic_py310_keystone_test = register_env_section(
    name='classic_py310_keystone_test',
    env_name='testenv:py310',
    basepython='python3.10',
    commands=(
        'make sync',
        'stestr run --slowest {posargs}',
    ),
    deps=('-r{toxinidir}/requirements.txt',
          ZOT_CLASSIC_TEST_REQUIREMENTS_TXT)
)

classic_pep8 = register_env_section(
    name='classic_pep8',
    env_name='testenv:pep8',
    deps=('flake8==3.9.2',
          'git+https://github.com/juju/charm-tools.git'),
    commands=('flake8 {posargs} --exclude=*/charmhelpers '
              '--ignore=E402,E226,W503,W504 '
              'hooks unit_tests actions lib files',
              'charm-proof'),
)


# Technique based heavily upon
# https://github.com/openstack/nova/blob/master/tox.ini
classic_cover = register_env_section(
    name='classic_cover',
    env_name='testenv:cover',
    setenv=('{[testenv]setenv}',
            'PYTHON=coverage run --branch --concurrency=multiprocessing '
            '--parallel-mode --source=. '
            '--omit=".tox/*,*/charmhelpers/*,unit_tests/*"'),
    commands=('coverage erase',
              'stestr run --slowest {posargs}',
              'coverage combine',
              'coverage html -d cover',
              'coverage xml -o cover/coverage.xml',
              'coverage report'),
    deps=('-r{toxinidir}/requirements.txt',
          ZOT_CLASSIC_TEST_REQUIREMENTS_TXT)
)

classic_cover_keystone_test = register_env_section(
    name='classic_cover_keystone_test',
    env_name='testenv:cover',
    setenv=('{[testenv]setenv}',
            'PYTHON=coverage run --branch --concurrency=multiprocessing '
            '--parallel-mode --source=. '
            '--omit=".tox/*,*/charmhelpers/*,unit_tests/*"'),
    commands=('coverage erase',
              'stestr run --slowest {posargs}',
              'make sync',
              'coverage combine',
              'coverage html -d cover',
              'coverage xml -o cover/coverage.xml',
              'coverage report'),
    deps=('-r{toxinidir}/requirements.txt',
          ZOT_CLASSIC_TEST_REQUIREMENTS_TXT)
)


# This may not work with Tox 4.
classic_venv = register_env_section(
    name='classic_venv',
    env_name='testenv:venv',
    basepython='python3',
    commands='{posargs}',
)


classic_func_noop = register_env_section(
    name='classic_func_noop',
    env_name='testenv:func-noop',
    basepython='python3',
    commands='functest-run-suite --help',
    deps=ZOT_CLASSIC_TEST_REQUIREMENTS_TXT,
)


classic_func = register_env_section(
    name='classic_func',
    env_name='testenv:func',
    basepython='python3',
    commands='functest-run-suite --keep-model',
    deps=ZOT_CLASSIC_TEST_REQUIREMENTS_TXT,
)


classic_func_smoke = register_env_section(
    name='classic_func_smoke',
    env_name='testenv:func-smoke',
    basepython='python3',
    commands='functest-run-suite --keep-model --smoke',
    deps=ZOT_CLASSIC_TEST_REQUIREMENTS_TXT,
)


classic_func_dev = register_env_section(
    name='classic_func_dev',
    env_name='testenv:func-dev',
    basepython='python3',
    commands='functest-run-suite --keep-model --dev',
    deps=ZOT_CLASSIC_TEST_REQUIREMENTS_TXT,
)


classic_func_target = register_env_section(
    name='classic_func_target',
    env_name='testenv:func-target',
    basepython='python3',
    commands='functest-run-suite --keep-model --bundle {posargs}',
    deps=ZOT_CLASSIC_TEST_REQUIREMENTS_TXT,
)


classic_func_target_centralised = register_env_section(
    name='classic_func_target_centralised',
    env_name='testenv:func-target',
    basepython='python3',
    commands=('functest-run-module zaza.openstack.select.charm.run_tests -- '
              '{charm} {branch} {posargs}'),
    deps='-r{toxinidir}/test-requirements.txt',
)


###
#
# release-tools/global/source (reactive) envs
#
###

# do we want to elimiate the tox inception for the built artifact?
# almost certainly we do.
source_testenv = register_env_section(
    name='source_testenv',
    env_name='testenv',
    skip_install=True,
    setenv=('VIRTUAL_ENV={envdir}',
            'PYTHONHASHSEED=0',
            'TERM=linux',
            'CHARM_LAYERS_DIR={toxinidir}/layers',
            'CHARM_INTERFACES_DIR={toxinidir}/interfaces',
            'JUJU_REPOSITORY={toxinidir}/build'),
    passenv=('no_proxy',
             'http_proxy',
             'https_proxy',
             'CHARM_INTERFACES_DIR',
             'CHARM_LAYERS_DIR',
             'JUJU_REPOSITORY'),
    deps='-r{toxinidir}/requirements.txt',
    allowlist_externals=('charmcraft',
                         'bash',
                         'tox',
                         '{toxinidir}/rename.sh'),
)


source_build_with_rename = register_env_section(
    name='source_build_with_rename',
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
    deps=("-rhttps://raw.githubusercontent.com/openstack-charmers/"
          "release-tools/master/global/source-zaza/build-requirements.txt"),
)


source_build = register_env_section(
    name='source_build',
    env_name="testenv:build",
    basepython="python3",
    # charmcraft clean is done to ensure that
    # `tox -e build` always performs a clean, repeatable build.
    # For faster rebuilds during development,
    # directly run `charmcraft -v pack && ./rename.sh`.
    commands=('charmcraft clean',
              'charmcraft -v pack',
              'charmcraft clean'),
)


source_build_reactive = register_env_section(
    name='source_build_reactive',
    env_name='testenv:build-reactive',
    basepython='python3',
    commands=(
        'charm-build --log-level DEBUG --use-lock-file-branches '
        '-o {toxinidir}/build/builds src {posargs}'),
)


source_build_reactive_binary_wheels = register_env_section(
    name='source_build_reactive_binary_wheels',
    env_name='testenv:build-reactive',
    basepython='python3',
    commands=(
        'charm-build --log-level DEBUG --use-lock-file-branches '
        '--binary-wheels-from-source '
        '-o {toxinidir}/build/builds src {posargs}'),
)


source_add_build_lock_file = register_env_section(
    name='source_add_build_lock_file',
    env_name='testenv:add-build-lock-file',
    basepython='python3',
    commands=(
        'charm-build --log-level DEBUG --write-lock-file '
        '-o {toxinidir}/build/builds src {posargs}'),
)


source_py3 = register_env_section(
    name='source_py3',
    env_name='testenv:py3',
    basepython='python3',
    deps='-r{toxinidir}/requirements.txt',
)


source_py310 = register_env_section(
    name='source_py310',
    env_name='testenv:py310',
    basepython='python3.10',
    deps='-r{toxinidir}/requirements.txt',
)


source_pep8 = register_env_section(
    name='source_pep8',
    env_name='testenv:pep8',
    deps=('flake8==3.9.2',
          'git+https://github.com/juju/charm-tools.git'),
    commands=('flake8 {posargs} --exclude=*/charmhelpers '
              '--ignore=E402,E226,W503,W504 '
              'hooks unit_tests actions lib files',
              'charm-proof'),
)


# Technique based heavily upon
# https://github.com/openstack/nova/blob/master/tox.ini
source_cover = register_env_section(
    name='source_cover',
    env_name='testenv:cover',
    setenv=('{[testenv]setenv}',
            'PYTHON=coverage run --branch --concurrency=multiprocessing '
            '--parallel-mode --source=. '
            '--omit=".tox/*,*/charmhelpers/*,unit_tests/*"'),
    commands=('coverage erase',
              'stestr run --slowest {posargs}',
              'coverage combine',
              'coverage html -d cover',
              'coverage xml -o cover/coverage.xml',
              'coverage report'),
    deps='-r{toxinidir}/requirements.txt',
)

source_venv = register_env_section(
    name='source_venv',
    env_name='testenv:venv',
    basepython='python3',
    commands='{posargs}',
)


PASSENV_FOR_REACTIVE_FUNCTIONAL_TESTS: Tuple[str, ...] = (
    '{[testenv]setenv}',
    'HOME',
    'TERM',
    'CS_*',
    'OS_*',
    'TEST_*',
)


source_func = register_env_section(
    name='source_func',
    env_name='testenv:func',
    passenv=PASSENV_FOR_REACTIVE_FUNCTIONAL_TESTS,
    basepython='python3',
    commands='functest-run-suite --keep-model',
    deps=ZOT_REACTIVE_TEST_REQUIREMENTS_TXT,
)


source_func_smoke = register_env_section(
    name='source_func_smoke',
    env_name='testenv:func-smoke',
    passenv=PASSENV_FOR_REACTIVE_FUNCTIONAL_TESTS,
    basepython='python3',
    commands='functest-run-suite --keep-model --smoke',
    deps=ZOT_REACTIVE_TEST_REQUIREMENTS_TXT,
)


source_func_dev = register_env_section(
    name='source_func_dev',
    env_name='testenv:func-dev',
    passenv=PASSENV_FOR_REACTIVE_FUNCTIONAL_TESTS,
    basepython='python3',
    commands='functest-run-suite --keep-model --dev',
    deps=ZOT_REACTIVE_TEST_REQUIREMENTS_TXT,
)


source_func_target = register_env_section(
    name='source_func_target',
    env_name='testenv:func-target',
    passenv=PASSENV_FOR_REACTIVE_FUNCTIONAL_TESTS,
    basepython='python3',
    commands='functest-run-suite --keep-model --bundle {posargs}',
    deps=ZOT_REACTIVE_TEST_REQUIREMENTS_TXT,
)


###
#
# machine operator framework charms
#
###


###
#
# K8s operator framework charms 'sunbeam'
#
###

k8s_testenv = register_env_section(
    name='k8s_testenv',
    env_name='testenv',
    skip_install=True,
    passenv=('HOME',
             'TERM',
             'CS_*',
             'OS_*',
             'TEST_*',
             'no_proxy',
             'http_proxy',
             'https_proxy',
             'JUJU_REPOSITORY'),
)


__THIS__ = pathlib.Path(pathlib.PurePath(__file__).parent.parent).resolve()

k8s_cover = register_env_section(
    name="k8s_cover",
    env_name='testenv:cover',
    set_env='PYTHON=coverage run',
    description="Auto-generated cover for k8s sunbeam charms",
    commands=str(__THIS__ / 'tools' / 'cover.sh'),
    deps=('coverage',
          'stestr',
          '-f{toxinidir}/requirements.txt',
          '-f{toxinddir}/test-requirements.txt'),
)


# interpolation vars for commands in k8s_pep8; not they are not f-strings as we
# want tox itself to interpolate {toxinidir}
k8s_pyproject = '{toxinidir}/pyproject.toml'
k8s_target_dirs = '{toxinidir}/src/ {toxinidir}/tests/'
k8s_lib_dir = '{toxinidir}/lib/'

k8s_pep8 = register_env_section(
    name='k8s_pep8',
    description='Auto-generated lint case for k8s sunbeam charms',
    env_name='testenv:pep8',
    commands=(
        f'codespell {k8s_target_dirs}',
        f'pflake8 --exclude {k8s_lib_dir}'
        f'--config {k8s_pyproject} {k8s_target_dirs}',
        f'isort --check-only --diff --skip-glob {k8s_lib_dir} '
        f'{k8s_target_dirs}',
        f'black --config {k8s_pyproject} --check --diff '
        f'--exclude {k8s_lib_dir} {k8s_target_dirs}'),
    deps=('black',
          # Do not install flake8 6.0.0 as there is a bug causing
          # issues loading plugins.
          # https://github.com/savoirfairelinux/flake8-copyright/issues/19
          'flake8!=6.0.0',
          'flake8-docstrings',
          'flake8-copyright',
          'flake8-builtins',
          'pyproject-flake8',
          'pep8-naming',
          'isort',
          'codespell'),
)


k8s_fmt = register_env_section(
    name='k8s_fmt',
    env_name='testenv:fmt',
    description='Autogenerated fmt tox env for k8s charms',
    commands=(f'isort --skip-glob {k8s_lib_dir} {k8s_target_dirs}',
              f'black --config {k8s_pyproject} --exclude {k8s_lib_dir} '
              f'{k8s_target_dirs}'),
    deps=('black',
          'isort'),
)


k8s_py3 = register_env_section(
    name='k8s_py3',
    description='Autogenerated py3 for k8s sunbeam charms',
    env_name='testenv:py3',
    basepython='python3',
    commands='stestr run --slowest',
    deps=('-f{toxinidir}/test-requirements.txt',
          'stestr'),
)


k8s_py310 = register_env_section(
    name='k8s_py310',
    description='Autogenerated py3 for k8s sunbeam charms',
    env_name='testenv:py310',
    basepython='python3.10',
    commands='stestr run --slowest',
    deps=('-f{toxinidir}/test-requirements.txt',
          'stestr'),
)


k8s_build = register_env_section(
    name='k8s_build',
    description='Autogenerated build for k8s sunbeam charms',
    env_name='testenv:build',
    allowlist_externals=('charmcraft',
                         '{toxinidir}/rename.sh'),
    commands=('charmcraft clean',
              'charmcraft -v pack'),
)


###
#
# Map selectors to envs
#
###

category = register_selector_name('category')
branch = register_selector_name('branch')
charm_type = register_selector_name('type')
charm = register_selector_name('charm')

# different categories
openstack_category = category('openstack')
any_category = category(default)
ceph_category = category('ceph')
ovn_category = category('ovn')

# branches supported.
master_branch = branch('master')

# charm_types
classic_charm = charm_type('classic')  # original classic charm
reactive_charm = charm_type('reactive')  # charms.reactive charm
k8s_charm = charm_type('k8s')  # ops k8s sunbeam charm
ops_charm = charm_type('ops')  # ops machine framework charm

# individual snowflakes
default_charms = charm(default)
keystone_charm = charm('keystone')

# now register the a set of envs against a set of selection criteria
# not used as openstack-master-default is more 'specific' in that it actually
# declares the defaults for charms.  If a charm didn't use a charm selector,
# then openstack-master would be selected.
register_mapping(
    name="any-classic-master",
    selectors=(any_category,
               master_branch,
               classic_charm),
    env_list=(classic_testenv,
              classic_build,
              classic_py310,
              classic_py3,
              classic_pep8,
              classic_cover,
              classic_venv,
              classic_func_noop,
              classic_func,
              classic_func_smoke,
              classic_func_dev,
              classic_func_target)
)


register_mapping(
    name="keystone-classic-master",
    selectors=(any_category,
               master_branch,
               classic_charm,
               keystone_charm),
    env_list=(classic_testenv,
              classic_sync_build,
              classic_py310_keystone_test,
              classic_py3_keystone_test,
              classic_pep8,
              classic_cover_keystone_test,
              classic_venv,
              classic_func_noop,
              classic_func,
              classic_func_smoke,
              classic_func_dev,
              classic_func_target_centralised)
)


register_mapping(
    name="any-reactive-master",
    selectors=(any_category,
               master_branch,
               reactive_charm),
    env_list=(source_testenv,
              source_build,
              source_add_build_lock_file,
              source_py310,
              source_py3,
              source_pep8,
              source_cover,
              source_venv,
              source_func,
              source_func_smoke,
              source_func_dev,
              source_func_target)
)


register_mapping(
    name='any-k8s-master',
    selectors=(any_category,
               master_branch,
               k8s_charm),
    env_list=(k8s_testenv,
              k8s_build,
              k8s_pep8,
              k8s_fmt,
              k8s_cover)
)
