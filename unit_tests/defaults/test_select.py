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

import unittest

from ..utils import BaseTestCase


# unit under test:
import buck.defaults.select as select

import buck.utils


class TestTox(BaseTestCase):

    def test_determine_category_is_k8s(self):
        self.patch_object(buck.utils, 'is_k8s_charm', return_value=True)
        self.assertEqual(select.determine_category(), select.K8S)

    def test_determine_category_is_ovn(self):
        self.patch_object(buck.utils, 'is_k8s_charm', return_value=False)
        self.patch_object(
            buck.utils, 'get_charm_name', return_value='ovn-dedicated-chassis')
        self.assertEqual(select.determine_category(), select.OVN)
        self.get_charm_name.return_value = 'ovn-chassis'
        self.assertEqual(select.determine_category(), select.OVN)
        self.get_charm_name.return_value = 'ovn-central'
        self.assertEqual(select.determine_category(), select.OVN)

    def test_determine_category_is_ceph(self):
        self.patch_object(buck.utils, 'is_k8s_charm', return_value=False)
        self.patch_object(
            buck.utils, 'get_charm_name', return_value='ceph-nfs')
        self.assertEqual(select.determine_category(), select.CEPH)
        self.get_charm_name.return_value = 'ceph-rbd-mirror'
        self.assertEqual(select.determine_category(), select.CEPH)

    def test_determine_category_is_misc(self):
        self.patch_object(buck.utils, 'is_k8s_charm', return_value=False)
        self.patch_object(
            buck.utils, 'get_charm_name', return_value='mysql-router')
        self.assertEqual(select.determine_category(), select.MISC)

    def test_determine_category_is_openstack(self):
        self.patch_object(buck.utils, 'is_k8s_charm', return_value=False)
        self.patch_object(
            buck.utils, 'get_charm_name', return_value='nova-compute')
        self.patch_object(
            buck.utils, 'get_gitreview_line',
            return_value='openstack/charm-nova-compute')
        self.assertEqual(select.determine_category(), select.OPENSTACK)
        self.get_gitreview_line.assert_called_once_with('project')

    def test_determine_category_unknown(self):
        self.patch_object(buck.utils, 'is_k8s_charm', return_value=False)
        self.patch_object(
            buck.utils, 'get_charm_name', return_value='nova-compute')
        self.patch_object(
            buck.utils, 'get_gitreview_line',
            return_value='openstack/nova')
        with self.assertRaises(RuntimeError):
            select.determine_category()

    def test_determine_charm_type(self):
        self.patch_object(
            buck.utils, 'get_charm_type', return_value=select.K8S)
        self.assertEqual(select.determine_charm_type(),
                         select.K8S)


    def test_get_branch_from_gitreview(self):
        self.patch_object(
            buck.utils, 'get_branch_name', return_value='test-branch')
        self.assertEqual(select.get_branch_from_gitreview(),
                         'test-branch')

    def test_get_charm_from_gitreview(self):
        self.patch_object(
            buck.utils, 'get_charm_name', return_value='test-charm')
        self.assertEqual(select.get_charm_from_gitreview(),
                         'test-charm')
