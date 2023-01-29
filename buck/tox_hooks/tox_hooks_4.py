from typing import Any, Dict, List

import configparser

from tox.config.cli.parser import ToxParser  # type: ignore
from tox.config.sets import EnvConfigSet  # type: ignore
from tox.execute import Outcome  # type: ignore
from tox.session.state import State  # type: ignore
from tox.tox_env.api import ToxEnv  # type: ignore
from tox.tox_env.register import ToxEnvRegister  # type: ignore

from buck.config import use_buck_config, Env, validate_env_vars
from buck.defaults.buckini import buck_ini_kv

### Tox hook functions as called from buck.tox_hooks.plugin_hook:

# These are the tox 4 hooks to configure the virtual tox.ini
# They are called from hook_start.py if the tox 4 is being used.
# Add a new type of runner; don't need this for buck
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    pass


def tox_add_option(parser: ToxParser) -> None:
    pass


def tox_add_core_config(core_conf: EnvConfigSet, state: State) -> None:
    state.envs.on_empty_fallback_py = False
    # Never, ever, access state.envs._defined_envs as it finalizes the
    # envs.  e.g. this is a big NO No:
    p = state.conf._src._parser
    # See if there *is* a buck config section; if so use that.
    try:
        config_keys = p.items('buck')
    except configparser.NoSectionError:
        config_keys = list(buck_ini_kv.items())
    # get the envs from the items
    resolved_selectors, envs = use_buck_config(config_keys)
    for env in envs:
        mapped_env = _transform_env_to_kv(resolved_selectors, env)
        env_name = mapped_env['env_name']
        p.add_section(env_name)
        for k, v in mapped_env.items():
            if k == 'env_name':
                continue
            try:
                p.set(env_name, k, v)
            except TypeError as e:
                raise TypeError(
                    f"Issue: {str(e)} with {env_name}, {k} -> {str(v)}")


def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:
    pass


def tox_before_run_commands(tox_env: ToxEnv) -> None:
    pass


def tox_after_run_commands(
        tox_env: ToxEnv, exit_code: int, outcomes: List[Outcome]) -> None:
    pass


def tox_on_install(
        tox_env: ToxEnv, arguments: Any, section: str, of_type: str) -> None:
    pass


def tox_env_teardown(tox_env: ToxEnv) -> None:
    pass


### Utility functions to take the tox env configuration and run it into tox 4.

def _transform_env_to_kv(substitutions: Dict[str, str], env: Env
                         ) -> Dict[str, str]:
    mapped_key = {k: "{" + k + "}" for k in substitutions.keys()}
    mapped_env = validate_env_vars(**env)
    subbed_env = {}
    for k, v in mapped_env.items():
        for key, substitution in substitutions.items():
            if mapped_key[key] in v:
                v = v.replace(mapped_key[key], substitution)
        subbed_env[k] = v
    return subbed_env

