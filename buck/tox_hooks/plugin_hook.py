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

try:
    from buck.tox_hooks import tox_hooks_3
    from tox import hookimpl as impl

    @impl
    def tox_configure(config):
        tox_hooks_3.tox_configure(config)
except ImportError:
    from buck.tox_hooks import tox_hooks_4
    from tox.plugin import impl  # type: ignore
    # import buck.config

    # configure the tox 4.0 plugin endpoints.
    @impl
    def tox_register_tox_env(register):
        tox_hooks_4.tox_register_tox_env(register)

    @impl
    def tox_add_option(parser):
        tox_hooks_4.tox_add_option(parser)

    @impl
    def tox_add_core_config(core_conf, state):
        tox_hooks_4.tox_add_core_config(core_conf, state)

    @impl
    def tox_add_env_config(env_conf, state):
        tox_hooks_4.tox_add_env_config(env_conf, state)

    @impl
    def tox_before_run_commands(tox_env):
        tox_hooks_4.tox_before_run_commands(tox_env)

    @impl
    def tox_after_run_commands(tox_env, exit_code, outcomes):
        tox_hooks_4.tox_after_run_commands(tox_env, exit_code, outcomes)

    @impl
    def tox_on_install(tox_env, arguments, section, of_type):
        tox_hooks_4.tox_on_install(tox_env, arguments, section, of_type)

    @impl
    def tox_env_teardown(tox_env):
        tox_hooks_4.tox_env_teardown(tox_env)
