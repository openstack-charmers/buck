
from typing import (Optional, Dict, List, Union, Type,
    Callable, Tuple)
from collections.abc import Iterable
from collections import OrderedDict
from dataclasses import dataclass
from functools import partial
import importlib


# Type definitions
EnvValuesType = Union[str, Iterable[str], bool]
Env = Dict[str, Dict[str, EnvValuesType]]
Selectors = Dict[str, Callable]
Mappings = Dict[str, 'Mapping']  # note forward reference.


# Module vars to hold registered envs and selectors
envs: Optional[Env] = None
selectors: Optional[Selectors] = None
mappings: Optional[Mappings] = None


class DuplicateKeyError(TypeError):
    """Error if an env is duplicated by name."""
    pass


class ParameterError(Exception):
    """Error raised if a parameter just isn't okay."""
    pass


class SelectionError(Exception):
    """Error raised is selection criteria don't match any mapping."""
    pass


class default:
    """Type to indicate default unambiguously."""
    _name = ":default:"

    @classmethod
    def __eq__(cls, other: Union[str, 'default', Type[object]]) -> bool:
        if isinstance(other, str):
            return cls._name == other
        try:
            return cls._name == other._name  # type: ignore
        except AttributeError:
            return False


def get_envs_singleton() -> Env:
    """Return the ENVS singleton."""
    global envs
    if envs is None:
        envs = {}
    return envs


def get_selectors_singleton() -> Selectors:
    global selectors
    if selectors is None:
        selectors = {}
    return selectors


def get_mappings_singleton() -> Mappings:
    global mappings
    if mappings is None:
        mappings = {}
    return mappings


def validate_env_vars(**data: EnvValuesType) -> Dict[str, str]:
    """Validate that the keys provided in data are of the correct type.

    If the env_name prefix is 'testenv' then the keys are verified; otherwise
    the type is detected and then converted to a string.  Any iterables are
    assummed to be joined by a newline.

    :param data: the key, values that make up the an env.
    :raises: TypeError if the value doesn't conform to the valid type.
    :raises: KeyError on an unknown key.
    """
    type_checks = dict(
        env_name=is_str,
        description=is_str,
        setenv=partial(is_str_or_iterable_str, ', '),
        set_env=partial(is_str_or_iterable_str, ', '),
        commands=partial(is_str_or_iterable_str, "\n"),
        allowlist_externals=partial(is_str_or_iterable_str, ', '),
        passenv=partial(is_str_or_iterable_str, ', '),
        pass_env=partial(is_str_or_iterable_str, ', '),
        deps=partial(is_str_or_iterable_str, "\n"),
        basepython=is_str,
        platform=is_str,
        parrallel_show_output=is_bool,
        recreate=is_bool,
        skip_install=is_bool,
        labels=partial(is_str_or_iterable_str, ', '),
    )
    mapped_data = {}

    for k, v in data.items():
        try:
            mapped_v = type_checks[k](v)
        except KeyError:
            raise KeyError(f"Unknown env key '{k}'")
        mapped_data[k] = mapped_v
    return mapped_data


def is_str_or_iterable_str(separator: str,
                           # v: Union[str, Iterable[str]]) -> str:
                           v: EnvValuesType) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, Iterable):
        for part in v:
            if not isinstance(part, str):
                raise TypeError(
                    f"For {v}, part '{part}' is not a str; is: {type(part)}")
        return separator.join(v)
    raise TypeError(f"'{v}' is not a str or iterable of str.  It is {type(v)}")

# def is_str(v: str) -> str:
def is_str(v: EnvValuesType) -> str:
    if not isinstance(v, str):
        raise TypeError(f"'{v}' is not a str.  It is {type(v)}")
    return v

# def is_bool(v: bool) -> str:
def is_bool(v: EnvValuesType) -> str:
    if not isinstance(v, bool):
        raise TypeError(f"'{v}' is not a bool. It is {type(v)}")
    return str(v)


def register_env_section(name: str, **data: EnvValuesType) -> str:
    """Register an env name and the data that goes with it."""
    # Just check at this point that the data is okay; it is transformed later
    # depending on whether it tis Tox 3 or Tox 4.
    validate_env_vars(**data)
    envs = get_envs_singleton()
    if name in envs:
        raise DuplicateKeyError(f"env identifier '{name}' is duplicated.")
    assert 'env_name' in data.keys(), \
        (f"The key 'env_name' must be in the data to register_env_section(),"
         f"for {name}")
    envs[name] = data
    return name


class SelectorMatcher:
    """A matcher that holds the category and criteria for a match.

    The matches may be a 'default' object, which means that it matches
    anything.  However, if it's default it must be the only item in the list.
    """

    def __init__(self, category: str, *matches: Union[str, default]):
        self.category: str = category
        self.matches: List[Union[str, default]] = list(matches)
        self._is_default = False
        if default in matches:
            if len(matches) != 1:
                raise ParameterError(
                    "The 'default' matcher is been provided, but is not "
                    "unique in the list.")
            self._is_default = True

    def __call__(self, category: str, to_match: str):
        """See if the matcher matches."""
        return (category == self.category and
                (self.is_default or to_match in self.matches))

    @property
    def is_default(self):
        return self._is_default


def selector_matcher_factory(category: str
                             ) -> Callable[..., SelectorMatcher]:
    def _selector_matcher_factory(*matches: Union[str, default]) -> SelectorMatcher:
        """Returns a matcher that when passed a string returns whether it matched.

        :param *matches: list of stings that this will match against.
        :returns: callable that takes a string and returns a bool of the match.
        """
        return SelectorMatcher(category, *matches)

    return _selector_matcher_factory


def register_selector_name(selector_name: str
                           ) -> Callable[..., SelectorMatcher]:
    selectors = get_selectors_singleton()
    # check if name is in the selectors
    if selector_name in selectors:
        raise DuplicateKeyError(
            f"Key {selector_name} is a duplicate "
            f"for registering selector names")
    # add a name and then provide a callable that is the thing that checks the
    callable = selector_matcher_factory(selector_name)
    selectors[selector_name] = callable
    return callable


@dataclass
class Mapping:
    """Map a set of selectors against a list of envs.

    This class essentially describes how a set of selectors (i.e. matches to
    various criteria) results in a list of envs that gets added to the dynamic
    tox.ini.
    """
    name: str
    selectors: List[SelectorMatcher]
    envs: List[Env]

    def match(self, criteria: Dict[str, str]) -> bool:
        """Match criteria to the selectors and return whether it's a match.

        :param criteria: dict of category -> matcher for matching.
        :returns: True if the criteria matched.
        """
        try:
            return all(s(s.category, criteria[s.category])
                       for s in self.selectors)
        except KeyError:
            return False


def register_mapping(name: str,
                     selectors: Iterable[SelectorMatcher],
                     env_list: Iterable[str],
                     ) -> Mapping:
    """Register a set of selector functions against a list of envs.

    This function registers a selectors (matches) to envs:

    # now register the a set of envs against a set of selection criteria

        register_mapping(
            selectors=(category('openstack'),
                       branch('master')),
            env_list=(pep8, ),
        )

    :param name: A unique ID to identify this mapping.
    :param selectors: The list of selectors that will be matchers.
    :param env_list: the list of environments associated with the selectors.
    """
    # check the selectors are are in fact selector matchers.
    selector_list = list(selectors)
    if not selector_list:
        raise ParameterError("Empty list of selectors.")
    for selector in selector_list:
        if not isinstance(selector, SelectorMatcher):
            raise TypeError(
                f"Selector {selector} is not a SelectorMatcher instance.")
    categories = set(s.category for s in selector_list)
    if len(categories) != len(selector_list):
        raise ParameterError(
            "Duplicate selectors in selectors list: {}"
            .format(', '.join(s.category for s in selector_list)))

    # now check that the envs are okay (i.e. no duplicates)
    envs = list(env_list)
    if not envs:
        raise ParameterError("Empty list of environments.")
    if len(set(envs)) != len(envs):
        raise ParameterError(
            f"Envs list has duplicate names: {','.join(envs)}")
    # Now check that the environments are unique.
    registered_envs = get_envs_singleton()
    picked_envs = []
    for env in envs:
        if env not in registered_envs:
            raise ParameterError(f"Env {env} has not be registered")
        picked_envs.append(registered_envs[env])
    env_names = set(env['env_name'] for env in picked_envs)
    if len(env_names) != len(picked_envs):
        raise ParameterError(
            "Duplicate env_name (tox env name) in the list: {}"
            .format(', '.join(f"{env}->{registered_envs[env]['env_name']}"
                              for env in picked_envs)))

    # Finally, we need to create the comparitor and then save it for resolving.
    mappings = get_mappings_singleton()
    if name in mappings:
        raise DuplicateKeyError(f"Mapping name: {name} already exists.")
    mappings[name] = Mapping(name=name,
                             selectors=selector_list,
                             envs=picked_envs)
    return mappings[name]


def resolve_envs_by_selectors(criteria: Dict[str, Union[str, str]]
                              ) -> List[Env]:
    """Resolves a dictionary of selectors into a list of envs.

    The criteria are is a dictionary of category:match_item to pick a set of
    selectors from the mappings.  The mappings may have a default. If a
    category is missing from a mapping, then then mapping criteria is less
    specific than the criteria provided; in this case it is attempted later.
    So the criteria is sorted from most specific to least specific and then
    tested to get the appropriate set of envs.

    :param criteria: A dictionary of category -> values to match against.
    :returns: a list of resolved envs.
    :raises: AttributeError if a selector doesn't exist.
    """
    mappings = get_mappings_singleton()
    # sort the mappings that have no more of the criteria in to test against.
    # first filter the mappings so that they only have the criteria that we can
    # match against.
    filtered_mappings: List[Mapping] = []
    criteria_keys = list(criteria.keys())
    num_criteria = len(criteria_keys)
    for mapping in mappings.values():
        if len(mapping.selectors) <= num_criteria:
            if set(s.category
                   for s in mapping.selectors).issubset(criteria_keys):
                filtered_mappings.append(mapping)
    # sort by length, with a default being lower than one of the same length.
    # Use a cmp function, as it's easier to reason about.
    def _key_mapping(k: Mapping) -> int:
        """Sort by length and then default.

        A str matches in a category are 'worth' 1000, whereas a 'default' match
        is worth 1.  Thus two str match categories are worth 2000, with a str +
        default being 1001, and a single category being 1000 (or 1 if default).
        """
        value: int = 0
        for selector in k.selectors:
            if selector.is_default:
                value += 1
            else:
                value += 1000
        return value

    sorted_mappings = sorted(filtered_mappings, key=_key_mapping, reverse=True)

    # Now see if any of the sorted mappings matches against the criteria
    for mapping in sorted_mappings:
        if mapping.match(criteria):
            return mapping.envs
    raise SelectionError(
        "Criteria {} didn't match any of the registers mappings."
        .format(', '.join(f"{k}->{v}" for k, v in criteria.items())))


def use_buck_config(config_list: List[Tuple[str, str]]
                    ) -> Tuple[OrderedDict, List[Env]]:
    """Use the [buck] section items to find and load the tox env config.

    The necessary keys values are:

        config_module = <python module containing env and selector configs>
        lookup = <key1> <key2> ...
        <key1> = [string|function]:value
        <key2> = [string|function]:value
        ...

    This function imports the config_module and returns the list of
    EnvValuesType key, value pairs that will be used to configure the tox envs.

    :param config_list: key, value pairs that define the loading of the config.
    :raises: AttributeError if any of the config data doesn't map to keys.
    :raises: AssertionError if the config isn't correct.
    :raises: Exception for other, unhandled, issues.
    :returns: a tuple of (resolved selectors as a dictionary,
                          envs as lis of Env objects)
    """
    # lowercase all the key names
    config: Dict[str, str] = {k.lower(): v for k, v in config_list}
    # first load the config; this will register the envs and the selectors to
    # those envs.
    importlib.import_module(config['config_module'])
    # Now get the lookup criteria order, lowercased
    selectors = [s.lower() for s in config['lookup'].split()]
    # resolve the lookup keys by using their values or a function.
    resolved_selectors = OrderedDict()
    for key in selectors:
        criteria = config[key]
        if criteria.startswith('string:'):
            resolved_selectors[key] = criteria[len('string:'):]
        elif criteria.startswith('function:'):
            function = resolve_function(criteria[len('function:'):])
            resolved_selectors[key] = function()
    # now using the selectors, get the envs
    return resolved_selectors, resolve_envs_by_selectors(resolved_selectors)


def resolve_function(fn: str) -> Callable:
    """Resolve a dotted string to a callable function.

    The dotted string is a list of modules, with the final one being the
    function.  It is always assumed to be an absolute module definition.

    :param fn: the dotting string ultately being a module.
    :returns: the Callable function.
    """
    parts = fn.strip().split('.')
    module_str = '.'.join(parts[:-1])
    function_str = parts[-1]
    module = importlib.import_module(module_str)
    return getattr(module, function_str)
