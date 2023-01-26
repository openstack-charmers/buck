### Default [buck] tox.ini configuration section as keys:

buck_ini_kv = dict(
    lookup="category branch type charm",
    category="function:buck.defaults.select.determine_category",
    branch="function:buck.defaults.select.get_branch_from_gitreview",
    type="function:buck.defaults.select.determine_charm_type",
    charm="function:buck.defaults.select.get_charm_from_gitreview",
    config_module="buck.defaults.config",
)

