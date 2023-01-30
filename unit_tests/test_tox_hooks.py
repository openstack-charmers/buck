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

from unittest import mock

from buck import tox_hooks


class TestTox(unittest.TestCase):
    def setUp(self):
        self.config = mock.MagicMock()

    def test_get_reader(self):
        tox = tox_hooks.Tox(self.config)
        tox.get_reader('tox')

    def test_add_envconfigs(self):
        tox = tox_hooks.Tox(self.config)
        tox.add_envconfigs([])
