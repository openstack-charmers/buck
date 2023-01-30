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
import os
import pathlib
import yaml

from typing import Optional

try:
    from functools import cache
except ImportError:
    from functools import lru_cache as cache

K8S = 'k8s'
CLASSIC = 'classic'
REACTIVE = 'reactive'
OPS = 'ops'
UNKNOWN = 'UNKNOWN'
DEFAULT_BRANCH = 'master'  # Charmed OpenStack hasn't migrated to 'main'.


@cache
def read_gitreview() -> Optional[configparser.ConfigParser]:
    cwd = os.getcwd()
    gitreview_path = os.path.join(cwd, '.gitreview')
    if not os.path.isfile(gitreview_path):
        return None

    config = configparser.ConfigParser()
    config.read(gitreview_path)
    return config


@cache
def read_metadata_file():
    with open('metadata.yaml', 'r') as f:
        contents = yaml.load(f, Loader=yaml.SafeLoader)
    return contents


def get_gitreview_line(key: str) -> Optional[str]:
    try:
        # if read_gitreview() returns None, typing complains that it isn't
        # scriptable; give it something that is, in the case of None.
        return (read_gitreview() or {})['gerrit'][key]
    except KeyError:
        return None


def is_k8s_charm():
    metadata = read_metadata_file()
    return metadata and 'containers' in metadata.keys()


def get_charm_type():
    if is_k8s_charm():
        return K8S
    # is it a reactive charm?
    filename = pathlib.PosixPath('.') / 'src' / 'layer.yaml'
    if filename.exists():
        return REACTIVE
    # is it an ops framework charm?
    filename = pathlib.PosixPath('.') / 'src' / 'charm.py'
    if filename.exists():
        return OPS
    # is it a classic; it will have a charm-helpers-hooks.yaml file
    filename = pathlib.PosixPath('.') / 'charm-helpers-hooks.yaml'
    if filename.exists():
        return CLASSIC
    # Don't know what it is.
    return UNKNOWN


def get_branch_name() -> str:
    return get_gitreview_line('defaultbranch') or DEFAULT_BRANCH


@cache
def get_charm_name() -> str:
    project = get_gitreview_line('project')
    if project is None:
        raise RuntimeError(
            "Can't find project in .gitreview?")
    charm = project.split('/')[1]
    if "." in charm:
        charm = charm.split('.')[0]
    if charm.startswith("charm-"):
        charm = charm[len("charm-"):]
    return charm
