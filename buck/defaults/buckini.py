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
#
# Default [buck] tox.ini configuration section as keys:

buck_ini_kv = dict(
    lookup="category branch type charm",
    category="function:buck.defaults.select.determine_category",
    branch="function:buck.defaults.select.get_branch_from_gitreview",
    type="function:buck.defaults.select.determine_charm_type",
    charm="function:buck.defaults.select.get_charm_from_gitreview",
    config_module="buck.defaults.config",
)
