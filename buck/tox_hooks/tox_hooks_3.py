import copy
import functools
import os
import re
from typing import (
    Callable,
    cast,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
)

from tox.config import (
    Config,
    DepConfig,
    DepOption,
    ParseIni,
    SectionReader,
    TestenvConfig,
)

from buck.config import (
    Env,
    EnvValuesType,
    ParameterError,
    use_buck_config,
)
from buck.defaults.buckini import buck_ini_kv


def tox_configure(config: Config) -> None:
    """Main hook for tox < 3

    Thsi configures tox with a list of environments depending on what the
    underlying charm is.

    :param config: the configuration from Tox.
    """
    config_keys = get_buck_config(config)
    # get the envs from the items
    resolved_selectors, envs = use_buck_config(config_keys)
    # now attempt to convert the envs into into TestenvConfig objects.
    buck_envlist_names = []
    prefix = 'tox' if config.toxinipath.basename == "setup.cfg" else None
    tox_reader = get_reader(config, "tox", prefix=prefix)
    _env_resolver = functools.partial(env_resolver, config, envs)
    for env in envs:
        testenv_config = make_tox3_env(tox_reader,
                                       _env_resolver,
                                       resolved_selectors,
                                       config,
                                       env)
        env_name = env['env_name']
        name = env_name.split(':')[-1] if ':' in env_name else env_name
        buck_envlist_names.append(name)
        config.envconfigs[name] = testenv_config

    # Don't filter down or add to envlist if an environment has been
    # specified by the user
    if hasattr(config, "envlist_explicit") and config.envlist_explicit:
        return

    # Add the items we generated to the envlist to be executed by default. Use
    # a Set, because there might be dupes.
    config.envlist = list(set(config.envlist + buck_envlist_names))
    envlist_default = copy.deepcopy(config.envlist)
    envlist_default.remove('build')
    envlist_default.remove('python')
    config.envlist.sort()
    config.envlist_default = envlist_default


def get_reader(config: Config, section: str, prefix: Optional[str] = None
               ) -> SectionReader:
    """Return a section reader for the passed param `section`.

    Create a SectionReader and configure it with known and reasonable
    substitution values based on the config.

    :param config: the Tox 3 Config object.
    :param str: The name of the section.
    :param prefix: the optional prefix for the section.
    :returns: a SectionReader for the named section.
    """
    # pylint: disable=protected-access
    reader = SectionReader(section, config._cfg, prefix=prefix)
    distshare_default = os.path.join(str(config.homedir), ".tox", "distshare")
    reader.addsubstitutions(
        toxinidir=config.toxinidir,
        homedir=config.homedir,
        toxworkdir=config.toxworkdir,
    )
    distdir = reader.getpath(
        "distdir", os.path.join(str(config.toxworkdir), "dist")
    )
    reader.addsubstitutions(distdir=distdir)
    distshare = reader.getpath("distshare", distshare_default)
    reader.addsubstitutions(distshare=distshare)
    return reader


def make_tox3_env(tox_reader: SectionReader,
                  resolver: Callable[[Env, str, type], EnvValuesType],
                  subs: Dict[str, str],
                  config: Config,
                  env: Env) -> TestenvConfig:
    """Make a TestenvConfig suitable for plugging into Tox 3 internals.

    This basically uses some of the internal functions in tox 3 to create a
    TestenvConfig object that can be plugged into tox 3.

    One problem is that we have to basically do the '[testenv]' inheritance if
    the env['env_name'] has the 'testenv:' prefix.  i.e. we need to do
    fallback.  We also need to do substitutions for if {[env_name]var} is used.
    This is a problem with using a common prefix.

    This is inspired by the ansible tox plugin, but using a functional approach
    as the class version doesn't really make sense.

    The resolver callable is used to resolve a (env, value) -> a value that
    has no more local substitutions. e.g

        value = resolver(env, key)

    :param tox_reader: a SectionReader for the tox section of the ini file.
    :param resolver: A callable that resolves a value to a fallback or that
        needs a buck substitution.
    :param config: the config from tox 3.
    :param env: a configuration Env to build the TestenvConfig.
    :returns: a configured TestenvConfig option.
    """
    make_envconfig = ParseIni.make_envconfig
    env_resolver = functools.partial(resolver, env)

    section: str = cast(str, env['env_name'])
    name = section.split(':')[-1] if ':' in section else section

    testenv = make_envconfig(config, name, section, tox_reader._subs, config)

    testenv.skipsdist = env_resolver('skipsdisk', bool)
    testenv.skip_install = env_resolver('skip_install', bool)
    testenv.description = env_resolver('description', str)

    # Now add it deps; also add in any that were defined at the top level.
    do = DepOption()
    processed_deps: List[DepConfig] = []
    deps = env_resolver('deps', list)
    if deps:
        deps = [interpolate_value(config, subs, dep)
                for dep in cast(list, deps)]
        processed_deps.extend(do.postprocess(testenv, deps))
    if testenv.deps:
        processed_deps = testenv.deps + processed_deps
    testenv.deps = processed_deps

    # Add additional items.
    _basepython = env_resolver('basepython', str)
    if _basepython is not None:
        testenv.basepython = _basepython
    testenv.commands = [
        interpolate_value(config, subs, s).split()
        for s in cast(list, env_resolver('commands', list))]

    # alias set_env and setenv to the same thing.
    set_env_list: List[str] = (
        cast(list, env_resolver('set_env', list) or []) +
        cast(list, env_resolver('setenv', list) or []))
    for pair in set_env_list:
        if '=' not in pair:
            raise TypeError(
                f"For env {env['env_name']}, resolved set_env has config that "
                f"has no '=': {pair}")
        k, v = pair.split('=', 1)
        testenv.setenv[k.strip()] = interpolate_value(config, subs, v)

    # Add in pass_env/passenv variables.
    pass_env_list: Set[str] = set(
        cast(list, env_resolver('pass_env', list) or []) +
        cast(list, env_resolver('passenv', list) or []))
    for v in pass_env_list:
        if v not in testenv.passenv:
            testenv.passenv.add(v)

    # now set the allowlist (formerly whitelist)
    if hasattr(testenv, "whitelist_externals"):
        allowlist = "whitelist_externals"
    else:
        allowlist = "allowlist_externals"
    allow_list_values = env_resolver('allowlist_externals', list)
    if allow_list_values and not getattr(testenv, allowlist):
        testenv.allowlist_externals = allow_list_values

    # finally return the configured testenv
    return testenv


def get_buck_config(config: Config) -> List[Tuple[str, str]]:
    try:
        config_keys = list(config._cfg.sections['buck'].items())
    except KeyError:
        config_keys = list(buck_ini_kv.items())
    return config_keys


T = TypeVar('T')


def env_resolver(config: Config,
                 envs: List[Env],
                 env: Env,
                 key: str,
                 return_type: type[T],
                 visited_envs: Optional[List[str]] = None
                 ) -> Optional[T]:
    """Resolve a `key` in `env` to it's value.

    The value is a EnvValuesType, and may contain references to other envs in
    the form of '{[envname]key}', in which case that should be used
    interpolated into the returned value as well.  If the env_name is of the
    form "prefix:name", then an env with an env_name of "prefix" is used as a
    fallback to provide the value.  Note that this function recurses as
    necessary (and visited_envs prevents infinite recursion.).

    This function doesn't resolve substitutions (e.g. {toxinidir}, {posargs},
    etc.) which are done by a value resolver.

    :param config: The config from tox 3
    :param envs: the envs being used for resolving values
    :param env: the actual env to do the resolving.
    :param key: the key that a value is needed for.
    :param return_type: the expected type of the return value
    :param visited_env: a list of envs that have been visited; catches
        recursive resolving loops.
    :returns: the resolved value for the key lookup.
    :raises: buck.config.ParameterError if the resolving can't resolve a value
        completely.
    """
    env_name = cast(str, env['env_name'])
    if visited_envs is None:
        visited_envs = []
    if env_name in visited_envs:
        raise ParameterError(
            f"Circular dependency on resolving a value: "
            f"{'->'.join(visited_envs)}")
    visited_envs.append(env_name)
    try:
        value = env[key]
    except KeyError:
        # see if we can lookup in a fallback env.
        if ':' in env_name:
            parts = env_name.split(':')
            fallback_env = ':'.join(parts[:-1])
            # ensure we aren't being circular
            if fallback_env in visited_envs:
                return None
            # find the env with the name fallback_env
            for _env in envs:
                if _env['env_name'] == fallback_env:
                    return env_resolver(config,
                                        envs,
                                        _env,
                                        key,
                                        return_type,
                                        visited_envs)
        return None
    # now see if the value requires a look up.
    # first work out what it is.
    values = [value] if isinstance(value, (str, bool)) else value
    resolved_values = []
    for v in values:
        new_v = _resolve_env_value(config,
                                   envs,
                                   v,
                                   return_type,
                                   visited_envs)
        if isinstance(new_v, str):
            resolved_values.append(new_v)
        elif isinstance(new_v, Iterable):
            resolved_values.extend(new_v)
        else:
            resolved_values.append(new_v)
    if return_type is list:
        return cast(T, resolved_values)
    if len(resolved_values) != 1:
        raise ParameterError(
            f"Return type is not list but more than one item for {key} "
            f"from env {env_name}, values: "
            f"{', '.join(str(v) for v in resolved_values)}")
    return resolved_values[0]


def _resolve_env_value(
    config: Config,
    envs: List[Env],
    value: EnvValuesType,
    return_type: type[T],
    visited: List[str],
) -> Optional[T]:
    if isinstance(value, str):
        m = re.match(r"^\{\[(\S+)\](\S+)\}$", value.strip())
        if m:
            if m.group(0) in visited:
                raise ParameterError(
                    f"Circular dependency for {m.group(0)} as already "
                    f"visisted: {'->'.join(visited)}")
            visited.append(m.group(0))
            _env_name = m.group(1)
            _key_name = m.group(2)
            for _env in envs:
                if _env['env_name'] == _env_name:
                    # recursively call env_resolver which will result in a
                    # resolved value
                    new_v = env_resolver(config, envs, _env, _key_name,
                                         return_type,
                                         cast(list, visited) + [m.group(0)])
                    if new_v is not None:
                        return new_v
                    raise ParameterError(
                        f"Couldn't interpolate '{value}' in env: {_env_name}")
            else:
                raise ParameterError(
                    f"Couldn't find env {_env_name} referenced from "
                    f"value {value} for key {_key_name}")
        # just return the value if there is no match.
        return cast(T, value)
    else:
        # is it a list of things
        if isinstance(value, Iterable):
            resolved_values = []
            for v in value:
                if isinstance(v, str):
                    resolved_values.append(_resolve_env_value(
                        config, envs, v, str, visited))
                else:
                    resolved_values.append(v)
            return cast(T, resolved_values)
        return cast(T, value)


def interpolate_value(config: Config,
                      substitutions: Dict[str, str],
                      value: str) -> str:
    """Do possible interpolations for variables and substitutions.

    This interpolates {var} in the string for the common variables.

    :param config: the Config which includes useful substitutions.
    :param substitutions: a dictionary of substitutions.
    :param value: the string to interpolate.
    :returns: the interpolated string.
    """
    subs = substitutions.copy()
    extra_subs = {
        'posargs': ' '.join(config.option.args),
        'toxinidir': str(config.toxinidir),
        'toxworkdir': str(config.toxworkdir),
        'homedir': str(config.homedir),
        'distshare': str(config.distshare),
    }
    for k, v in extra_subs.items():
        if k not in subs:
            subs[k] = v

    # Now do the subs.
    for k, v in subs.items():
        sub = '{' + k + '}'
        value = value.replace(sub, v)
    return value
