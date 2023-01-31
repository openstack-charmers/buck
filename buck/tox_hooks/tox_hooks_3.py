import copy
import functools
import os
from typing import (
    Callable,
    cast,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
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
    env_resolver,
    EnvValuesType,
    use_buck_config,
)


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
    prefix = ('tox' if config.toxinipath.basename == "setup.cfg"  # type:ignore
              else None)
    tox_reader = get_reader(config, "tox", prefix=prefix)
    _env_resolver = functools.partial(env_resolver, envs)
    for env in envs:
        testenv_config = make_tox3_env(tox_reader,
                                       _env_resolver,  # type:ignore
                                       resolved_selectors,
                                       config,
                                       env)
        env_name = cast(str, env['env_name'])
        name = env_name.split(':')[-1] if ':' in env_name else env_name
        buck_envlist_names.append(name)
        config.envconfigs[name] = testenv_config

    # Don't filter down or add to envlist if an environment has been
    # specified by the user
    if (hasattr(config, "envlist_explicit") and
            config.envlist_explicit):  # type:ignore
        return

    # Add the items we generated to the envlist to be executed by default. Use
    # a Set, because there might be dupes.
    config.envlist = list(  # type:ignore
        set(config.envlist + buck_envlist_names))  # type:ignore
    envlist_default = copy.deepcopy(config.envlist)  # type:ignore
    envlist_default.remove('build')
    envlist_default.remove('python')
    config.envlist.sort()  # type:ignore
    config.envlist_default = envlist_default  # type:ignore


def get_buck_config(config: Config) -> List[Tuple[str, str]]:
    try:
        config_keys = list(config._cfg.sections['buck'].items())  # type:ignore
    except KeyError:
        # only import here if needed
        from buck.defaults.buckini import buck_ini_kv
        config_keys = list(buck_ini_kv.items())
    return config_keys


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
    reader = SectionReader(section, config._cfg, prefix=prefix)  # type:ignore
    distshare_default = os.path.join(str(config.homedir), ".tox", "distshare")
    reader.addsubstitutions(
        toxinidir=config.toxinidir,  # type:ignore
        homedir=config.homedir,
        toxworkdir=config.toxworkdir,  # type:ignore
    )
    distdir = reader.getpath(
        "distdir", os.path.join(str(config.toxworkdir), "dist")  # type:ignore
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

    testenv = make_envconfig(config,  # type:ignore
                             name, section, tox_reader._subs, config)

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
        'toxinidir': str(config.toxinidir),  # type:ignore
        'toxworkdir': str(config.toxworkdir),  # type:ignore
        'homedir': str(config.homedir),
        'distshare': str(config.distshare),  # type:ignore
    }
    for k, v in extra_subs.items():
        if k not in subs:
            subs[k] = v

    # Now do the subs.
    for k, v in subs.items():
        sub = '{' + k + '}'
        value = value.replace(sub, v)
    return value
