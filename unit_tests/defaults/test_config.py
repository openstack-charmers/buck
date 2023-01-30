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

from typing import cast

import unittest
import importlib

# Note importing buck_config automatically tests that the module imports and
# that the keys are valid, etc.  These tests are checks that they envs sets are
# consistent.

import buck.config as buck_config
# unit under test:
import buck.defaults.config as envs_config



class TestTox(unittest.TestCase):

    def test_testenv_sanity(self):
        mappings = buck_config.mappings
        self.assertIsNotNone(mappings)
        for mapping_name, mapping in cast(dict, mappings).items():
            env_names = [env['env_name'] for env in mapping.envs]
            self.assertEqual(len(env_names), len(set(env_names)))
            prefixes = set([e.split(':')[0] for e in env_names
                            if ':' in e])
            # ensure that a prefix env exists.
            for prefix in prefixes:
                self.assertIn(
                    prefix,
                    env_names,
                    f"Prefix {prefix} is missing from {', '.join(env_names)} "
                    f"for mapping {mapping_name}")

            # ensure that every env has a basepython defined.
            for env in mapping.envs:
                # TODO: can't do this until env_resolver is refactored into
                # buck.config
                pass






