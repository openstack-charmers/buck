
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

