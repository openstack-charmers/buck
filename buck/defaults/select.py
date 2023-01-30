import buck.utils


K8S = 'k8s'
OPENSTACK = 'openstack'
CEPH = 'ceph'
OVN = 'ovn'
MISC = 'misc'

default_categories = (
    K8S,
    OPENSTACK,
    CEPH,
    OVN,
    MISC,
)

OVN_CHARMS = (
    'ovn-dedicated-chassis',
    'ovn-chassis',
    'ovn-central',
)

CEPH_CHARMS = (
    'ceph-dashboard',
    'ceph-fs',
    'ceph-iscsi',
    'ceph-mon',
    'ceph-osd',
    'ceph-nfs',
    'ceph-proxy',
    'ceph-radosgw',
    'ceph-rbd-mirror',
)

MISC_CHARMS = (
    'hacluster',
    'magpie',
    'mysql-innodb-cluster',
    'mysql-router',
    'percona-cluster',
    'rabbitmq-server',
    'vault',
    'openstack-loadbalancer',
    'pacemaker-remote',
)

# OPENSTACK charms are 'everything else in the openstack/charm-* opendev
# project space.'


def determine_category() -> str:
    """Determine the category of the charm.

    :returns: the category as a string."""
    if buck.utils.is_k8s_charm():
        return K8S
    charm = buck.utils.get_charm_name()
    if charm in OVN_CHARMS:
        return OVN
    if charm in CEPH_CHARMS:
        return CEPH
    if charm in MISC_CHARMS:
        return MISC
    # check that the project-line startswith "openstack/charm-"
    project = buck.utils.get_gitreview_line('project')
    if project is None:
        raise RuntimeError(
            "Can't find project in .gitreview?")
    if project.startswith('openstack/charm-'):
        return OPENSTACK
    raise RuntimeError("Can't determine what the charm category is.")


def determine_charm_type() -> str:
    """Determine the charm type.

    It will be one of:

     - classic
     - reactive
     - k8s
     - ops
     - unknown

    :returns: the charm type.
    """
    return buck.utils.get_charm_type()


def get_branch_from_gitreview() -> str:
    return buck.utils.get_branch_name()


def get_charm_from_gitreview() -> str:
    return buck.utils.get_charm_name()
