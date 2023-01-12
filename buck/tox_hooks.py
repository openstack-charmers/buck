import copy
import os
from typing import List, Set
from tox import hookimpl
from tox.config import DepOption, ParseIni, SectionReader, testenvprefix

import buck.utils as utils

__THIS__ = os.path.dirname(os.path.abspath(__file__))


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
        return [[os.path.join(__THIS__, 'tools/cover.sh')]]

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
             "stestr"])


class ToxPy310Case(ToxPy3Case):
    name = 'py310'
    description = 'Auto-generated py310'
    basepython = 'python3.10'


class ToxCharmcraftBuildCase(BaseCase):
    name = 'build'
    description = 'Auto-generated build'

    @property
    def commands(self):
        return [["charmcraft", "clean"],
                ["charmcraft", "-v", "pack"]]

    @property
    def dependencies(self):
        return set()


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
                                          "charmcraft"]


@hookimpl
def tox_configure(config):

    tox = Tox(config)

    # map of tox cases based on the charm type and the branch
    # {<charm_type>: {<git_branch>: [<list of cases>] } }
    all_tox_cases = {
        utils.K8S: {
            'main': [
                ToxCharmcraftBuildCase(config),
                ToxK8SLintCase(config),
                ToxK8SFMTCase(config),
                ToxCoverCase(config)],
        },
        utils.UNKNOWN: {
            'main': [
                ToxLintCase(config),
                ToxPy3Case(config),
                ToxPy310Case(config),
                ToxCharmcraftBuildCase(config),
                ToxCoverCase(config)],
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
