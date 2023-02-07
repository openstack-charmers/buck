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

import argparse
import copy
import logging
import os
import subprocess

from buck import utils
from jinja2 import Environment, FileSystemLoader, select_autoescape

__THIS__ = os.path.dirname(os.path.abspath(__file__))
LOG = logging.getLogger(__name__)
KNOWN_FILES = [
    # relative to the toplevel directory of the git repo.
    ('src/config.yaml.j2', 'src/config.yaml'),
    ('.zuul.yaml.j2', '.zuul.yaml'),
]

OPENSTACK_INFO = {
    'origin': 'zed'
}


def setup_opts():
    parser = argparse.ArgumentParser(description='buck automation.')
    subparsers = parser.add_subparsers(title='subcommands', required=True,
                                       dest='cmd')
    up = subparsers.add_parser('up')
    up.set_defaults(func=cmd_up)

    return parser.parse_args()


def cmd_up(args):
    cwd = os.getcwd()
    env = Environment(
        loader=FileSystemLoader([cwd, os.path.join(__THIS__, 'templates')]),
        autoescape=select_autoescape()
    )
    print('CWD', cwd)
    for in_file, out_file in KNOWN_FILES:

        result = subprocess.run(['git', 'ls-files', '--error-unmatch',
                                 os.path.join(cwd, out_file)], check=False,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        if result.returncode == 0:
            # the file is tracked by git, so we skip overriding it.
            print(f'Skipping {out_file}, reason: tracked by git')
            continue

        print(f'Using {in_file} template')
        template = env.get_template(in_file)

        os_info = copy.deepcopy(OPENSTACK_INFO)
        gitreview = utils.read_gitreview()
        try:
            defaultbranch = gitreview['gerrit']['defaultbranch']
            os_info['origin'] = defaultbranch.split('/')[-1]
        except Exception as ex:
            LOG.debug(str(ex))
            LOG.info(('defaultbranch is not set in .gitreview file, '
                      'falling back to %s'), utils.DEFAULT_BRANCH)
            os_info['origin'] = utils.DEFAULT_BRANCH

        result = template.stream({'openstack': os_info,
                                  'gitreview': gitreview})

        print(f'Writing {out_file}...', end='')
        with open(out_file, 'w') as f:
            result.dump(f)
            f.write('\n')
        print('done')


def main():
    args = setup_opts()
    args.func(args)
