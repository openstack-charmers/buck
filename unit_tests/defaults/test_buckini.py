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

import unittest
import importlib


# unit under test:
import buck.defaults.buckini as buckini


class TestTox(unittest.TestCase):

    def test_buckini_kv_is_valid(self):
        kv = buckini.buck_ini_kv
        self.assertIn('lookup', kv, "Missing 'lookup' from defaults")
        self.assertIn('config_module', kv, "Missing 'config_module'")

        # validate that the config module is loadable
        try:
            importlib.import_module(kv['config_module'])
        except Exception as e:
            raise self.failureException(
                f"config module '{kv['config_module']} failed to import: "
                f"due to: {str(e)}")

        # now verify that the look up keys exist.
        keys = [s.strip() for s in kv['lookup'].split(' ')]
        for key in keys:
            self.assertIn(key, kv, f"Missing key '{key}' in defaults")

        # finally verify that the categories are strings or functions, and if
        # they are functions that they are importable and exist.
        for key in keys:
            category = kv[key]
            self.assertIn(':', category, f"missing ':' in {key} -> {category}")
            _type, value = category.split(':', 1)
            self.assertIn(_type, ('function', 'string'))
            if _type == "function":
                parts = value.split('.')
                module = ".".join(parts[:-1])
                function = parts[-1]
                try:
                    the_module = importlib.import_module(module)
                except Exception as e:
                    raise self.failureException(
                        f"function module '{module}' failed to import: "
                        f"due to: {str(e)}")
                # verify that the function exists
                getattr(the_module, function)
