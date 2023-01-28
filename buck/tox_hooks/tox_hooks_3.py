import copy
import functools
import os
import pathlib
import re
from typing import (Iterable, List, Set, Dict, Tuple, Optional, Callable, cast, Type,
    TypeVar)

from tox import hookimpl
from tox.config import (
    Config,
    DepOption,
    DepConfig,
    ParseIni,
    SectionReader,
    testenvprefix,
    TestenvConfig,
)

from buck.config import (use_buck_config, Env, validate_env_vars, EnvValuesType,
    ParameterError)
from buck.defaults.buckini import buck_ini_kv
import buck.utils as utils


__THIS__ = pathlib.Path(pathlib.PurePath(__file__).parent.parent).resolve()


passenv_list = (
    "HOME",
    "OS_*",
    "TEST_*",
    "no_proxy", "http_proxy", "https_proxy",
    "JUJU_REPOSITORY",
)


class BaseCase(object):
    basepython = 'python3'

    def __init__(self, config):
        self._config = config

    @property
    def toxinidir(self):
        return self._config.toxinidir

    @property
    def setenv(self):
        return {}


class ToxCoverCase(BaseCase):
    name = 'cover'
    description = 'Auto-generated cover case'

    @property
    def commands(self) -> List[List[str]]:
        return [[str(__THIS__ / 'tools' / 'cover.sh')]]

    @property
    def setenv(self):
        return {"PYTHON": "coverage run"}

    @property
    def dependencies(self) -> Set[str]:
        return set(['coverage',
                    'stestr',
                    f'-r{self.toxinidir}/requirements.txt',
                    f'-r{self.toxinidir}/test-requirements.txt',
                    ])


class ToxLintCase(BaseCase):
    name = 'pep8'
    description = 'Auto-generated lint case'

    @property
    def commands(self):
        return [
            ["flake8", "src"]
        ]

    @property
    def dependencies(self):
        return set(["flake8"])


class K8SBaseCase(BaseCase):

    @property
    def pyproject(self):
        return f"{self.toxinidir}/pyproject.toml"

    @property
    def target_dirs(self):
        return [f"{self.toxinidir}/src/", f"{self.toxinidir}/tests/"]

    @property
    def lib_dir(self):
        return f"{self.toxinidir}/lib/"


class ToxK8SLintCase(K8SBaseCase):
    name = 'pep8'
    description = 'Auto-generated lint case'

    @property
    def commands(self):
        return [
            ["codespell"] + self.target_dirs,
            ["pflake8", "--exclude", f"{self.lib_dir}", "--config",
             f"{self.pyproject}"] + self.target_dirs,
            ["isort", "--check-only", "--diff", "--skip-glob",
             f"{self.toxinidir}/lib/"] + self.target_dirs,
            ["black", "--config", f"{self.pyproject}", "--check", "--diff",
             "--exclude", f"{self.lib_dir}"] + self.target_dirs,
        ]

    @property
    def dependencies(self):
        return set([
            "black",
            # Do not install flake8 6.0.0 as there is a bug causing
            # issues loading plugins.
            # https://github.com/savoirfairelinux/flake8-copyright/issues/19
            "flake8!=6.0.0",
            "flake8-docstrings",
            "flake8-copyright",
            "flake8-builtins",
            "pyproject-flake8",
            "pep8-naming",
            "isort",
            "codespell"])


class ToxK8SFMTCase(K8SBaseCase):
    name = 'fmt'
    description = 'Auto-generated fmt case'

    @property
    def commands(self):
        return [
            ["isort", "--skip-glob",
             f"{self.toxinidir}/lib/"] + self.target_dirs,
            ["black", "--config", f"{self.pyproject}",
             "--exclude", f"{self.lib_dir}"] + self.target_dirs,
        ]

    @property
    def dependencies(self):
        return set([
            "black",
            "isort"])


class ToxPy3Case(BaseCase):
    name = 'py3'
    description = 'Auto-generated py3'
    basepython = 'python3'

    @property
    def commands(self):
        return [["stestr", "run", "--slowest"]]

    @property
    def dependencies(self):
        return set(
            [f"-r{self.toxinidir}/test-requirements.txt",
            # ["-rhttps://raw.githubusercontent.com/openstack-charmers/release-tools/master/global/classic-zaza/test-requirements.txt",
             "stestr"])


class ToxPy310Case(ToxPy3Case):
    name = 'py310'
    description = 'Auto-generated py310'
    basepython = 'python3.10'


class ToxCharmcraftBuildK8sCase(BaseCase):
    name = 'build'
    description = 'Auto-generated build'

    @property
    def commands(self):
        return [["charmcraft", "clean"],
                ["charmcraft", "-v", "pack"]]

    @property
    def dependencies(self) -> Set[str]:
        return set()


class ToxCharmcraftBuildRenameCase(BaseCase):
    name = 'build'
    description = 'Auto-generated build'

    @property
    def commands(self) -> List[List[str]]:
        return [["charmcraft", "clean"],
                ["charmcraft", "-v", "pack"],
                [f"{self.toxinidir}/rename.sh"]]

    @property
    def dependencies(self) -> Set[str]:
        return set([f"-r{self.toxinidir}/build-requirements.txt"])


class ToxCharmcraftSyncBuildRenameCase(BaseCase):
    name = 'build'
    description = 'Auto-generated build'

    @property
    def commands(self) -> List[List[str]]:
        return [["make", "sync"],
                ["charmcraft", "clean"],
                ["charmcraft", "-v", "pack"],
                [f"{self.toxinidir}/rename.sh"]]

    @property
    def dependencies(self) -> Set[str]:
        return set(
            # [f"-r{self.toxinidir}/build-requirements.txt"])
            ["-rhttps://raw.githubusercontent.com/ajkavanagh/release-tools/add-bases-to-lp-config/global/classic-zaza/build-requirements.txt"])




class ToxPep8Case(BaseCase):
    name = 'pep8'
    description = "Auto-generated pep8 test case"

    @property
    def dependencies(self) -> Set[str]:
        return set(
            ["flake8==3.9.2",
             "charm-tools==2.8.4"])

    @property
    def commands(self) -> List[List[str]]:
        return [
            ["flake8"] + self._config.option.args +
             "hooks unit_tests tests actions lib files".split(),
            ["charm-proof"]]


class ToxFuncModuleCase(BaseCase):
    name = 'func-target'
    description = "Auto-generated debug test case"

    @property
    def dependencies(self) -> Set[str]:
        return set(
            [f"-r{self.toxinidir}/test-requirements.txt",
             # f"-r{self.toxinidir}/requirements.txt"])
            # ["-rhttps://raw.githubusercontent.com/openstack-charmers/release-tools/master/global/classic-zaza/test-requirements.txt",
             "-rhttps://raw.githubusercontent.com/openstack-charmers/release-tools/master/global/classic-zaza/requirements.txt"])

    @property
    def commands(self) -> List[List[str]]:
        branch = utils.get_branch_name()
        if '/' in branch:
            branch = branch.split('/')[-1]
        return [["functest-run-module",
                 "zaza.openstack.select.charm.run_tests",
                 utils.get_charm_name(), branch] + self._config.option.args]


# Forked from tox-ansible plugin.
class Tox(object):
    instance = None
    """A class that handles interacting with the specific internals of the tox
    world for the plugin."""

    def __new__(cls, *args):
        if cls.instance is None:
            cls.instance = super(Tox, cls).__new__(cls)
        return cls.instance

    def __init__(self, config=None):
        """Initialize this object

        :param config: the tox config object"""
        if config is not None:
            self.config = config

    def get_reader(self, section, prefix=None):
        """Creates a SectionReader and configures it with known and reasonable
        substitution values based on the config.

        :param section: Config section name to read from
        :param prefix: Any applicable prefix to the ini section name. Default
        None"""
        # pylint: disable=protected-access
        reader = SectionReader(section, self.config._cfg, prefix=prefix)
        distshare_default = os.path.join(str(self.config.homedir),
                                         ".tox", "distshare")
        reader.addsubstitutions(
            toxinidir=self.config.toxinidir,
            homedir=self.config.homedir,
            toxworkdir=self.config.toxworkdir,
        )
        self.config.distdir = reader.getpath(
            "distdir", os.path.join(str(self.config.toxworkdir), "dist")
        )
        reader.addsubstitutions(distdir=self.config.distdir)
        self.config.distshare = reader.getpath("distshare", distshare_default)
        reader.addsubstitutions(distshare=self.config.distshare)
        return reader

    @property
    def posargs(self):
        """Returns any configured posargs from the tox world"""
        return self.config.option.args

    @property
    def toxinidir(self):
        """Returns the configured toxinidir for working with base directory"""
        return self.config.toxinidir

    @property
    def opts(self):
        """Return the options as a dictionary-style object.

        :return: A dictionary of the command line options"""
        return vars(self.config.option)

    def add_envconfigs(self, tox_cases):
        """Modifies the list of envconfigs in tox to add any that were
        generated by this plugin.

        :param tox_cases: An iterable of test cases to create environments
        from"""
        # Stripped down version of parseini.__init__ for making a generated
        # envconfig
        if self.config.toxinipath.basename == "setup.cfg":
            prefix = "tox"
        else:
            prefix = None
        reader = self.get_reader("tox", prefix=prefix)
        make_envconfig = ParseIni.make_envconfig
        # Python 2 fix
        make_envconfig = getattr(make_envconfig, "__func__", make_envconfig)

        # Store the generated envlist
        self.config.buck_envlist = []
        for tox_case in tox_cases:
            section = testenvprefix + tox_case.name

            config = make_envconfig(
                self.config, tox_case.name, section, reader._subs, self.config
            )
            config.tox_case = tox_case

            # We do not want to install packages
            config.skipsdist = True
            config.skip_install = True

            self.customize_envconfig(config)
            for v in passenv_list:
                if v not in config.passenv:
                    config.passenv.add(v)

            self.config.envconfigs[tox_case.name] = config
            self.config.buck_envlist.append(tox_case.name)

    def customize_envconfig(self, config):
        """Writes the fields of the envconfig that need to be given default
        molecule related values.

        :param config: the constructed envconfig for this to customize"""
        tox_case = config.tox_case
        if not config.description:
            config.description = tox_case.description

        do = DepOption()
        processed_deps = do.postprocess(config, tox_case.dependencies)
        if config.deps:
            processed_deps = config.deps + processed_deps
        config.deps = processed_deps

        config.basepython = tox_case.basepython
        config.commands = tox_case.commands
        if tox_case.setenv:
            for key, value in tox_case.setenv.items():
                config.setenv[key] = value

        if hasattr(config, "whitelist_externals"):
            allowlist = "whitelist_externals"
        else:
            allowlist = "allowlist_externals"

        if not getattr(config, allowlist):
            config.allowlist_externals = ["{toxinidir}/rename.sh",
                                          "charmcraft",
                                          "make"]



def tox_configure(config: Config) -> None:
    """Main hook for tox < 3

    Thsi configures tox with a list of environments depending on what the
    underlying charm is.

    :param config: the configuration from Tox.
    """
    print(type(config))
    print(config)
    print(config.envconfigs)
    config_keys = get_buck_config(config)
    # get the envs from the items
    resolved_selectors, envs = use_buck_config(config_keys)
    print('envs', envs)
    # now attempt to convert the envs into into TestenvConfig objects.
    buck_envlist_names = []
    if config.toxinipath.basename == "setup.cfg":
        prefix = "tox"
    else:
        prefix = None
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
    # python_env = config.envconfigs['python']
    try:
        # config_keys = list(python_env._reader._cfg.sections['buck'].items())
        config_keys = list(config._cfg.sections['buck'].items())
    except KeyError:
        config_keys = list(buck_ini_kv.items())
    print("buck_config", config_keys)
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
    # print(f'Value: {type(value)} = {value}')
    for k, v in subs.items():
        # print(f'sub {k} -> {v} ({type(v)})')
        sub = '{' + k + '}'
        value = value.replace(sub, v)
    return value


def old_tox_configure(config):
    """Main hook for tox < 3

    This configures tox with the environments depending on what the underlying
    charm is.

    :param config: the configuration from Tox.
    """
    tox = Tox(config)

    # map of tox cases based on the charm type and the branch
    # {<charm_type>: {<git_branch>: [<list of cases>] } }
    all_tox_cases = {
        utils.K8S: {
            'main': [
                ToxCharmcraftBuildK8sCase(config),
                ToxK8SLintCase(config),
                ToxK8SFMTCase(config),
                ToxCoverCase(config)],
        },
        utils.UNKNOWN: {
            'main': [
                ToxLintCase(config),
                ToxPy3Case(config),
                ToxPy310Case(config),
                ToxCharmcraftBuildRenameCase(config),
                ToxCoverCase(config)],
            'master': [
                ToxPep8Case(config),
                ToxPy3Case(config),
                ToxPy310Case(config),
                # ToxCharmcraftBuildRenameCase(config),
                ToxCharmcraftSyncBuildRenameCase(config),
                ToxFuncModuleCase(config),
                ToxCoverCase(config)],
                # Flake8Config],
        },
    }

    tox_cases = all_tox_cases[utils.get_charm_type()][utils.get_branch_name()]

    # Add them to the envconfig list before testing for explicit calls, because
    # we want the user to be able to specifically state an auto-generated
    # test, if they want to
    tox.add_envconfigs(tox_cases)

    # Don't filter down or add to envlist if an environment has been
    # specified by the user
    if hasattr(config, "envlist_explicit") and config.envlist_explicit:
        return

    # Add the items we generated to the envlist to be executed by default
    # Set, because there might be dupes
    config.envlist = list(set(config.envlist + config.buck_envlist))
    envlist_default = copy.deepcopy(config.envlist)
    envlist_default.remove('build')
    envlist_default.remove('python')
    config.envlist.sort()
    config.envlist_default = envlist_default
    config.sitepackages = False
