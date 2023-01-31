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

"""Module to provide helper for writing unit tests."""

import contextlib
from dataclasses import dataclass
import io
import sys
from typing import Any, Dict
from unittest import mock
import unittest


@contextlib.contextmanager
def patch_open():
    """Patch open().

    Patch open() to allow mocking both open() itself and the file that is
    yielded.

    Yields the mock for "open" and "file", respectively.
    """
    mock_open = mock.MagicMock(spec=open)
    mock_file = mock.MagicMock(spec=io.FileIO)

    @contextlib.contextmanager
    def stub_open(*args, **kwargs):
        mock_open(*args, **kwargs)
        yield mock_file

    with mock.patch('builtins.open', stub_open):
        yield mock_open, mock_file


class BaseTestCase(unittest.TestCase):
    """Base class for creating classes of unit tests."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._patches = {}
        self._patches_start = {}

    def shortDescription(self):
        """Disable reporting unit test doc strings rather than names."""
        return None

    def setUp(self):
        """Run setup of patches."""
        self._patches = {}
        self._patches_start = {}

    def tearDown(self):
        """Run teardown of patches."""
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch_object(self, obj, attr, return_value=None, name=None, new=None,
                     **kwargs):
        """Patch the given object."""
        if name is None:
            name = attr
        if new is not None:
            mocked = mock.patch.object(obj, attr, new=new, **kwargs)
        else:
            mocked = mock.patch.object(obj, attr, **kwargs)
        self._patches[name] = mocked
        started = mocked.start()
        if new is None:
            started.return_value = return_value
        self._patches_start[name] = started
        setattr(self, name, started)

    def patch(self, item, return_value=None, name=None, new=None, **kwargs):
        """Patch the given item."""
        if name is None:
            raise RuntimeError("Must pass 'name' to .patch()")
        if new is not None:
            mocked = mock.patch(item, new=new, **kwargs)
        else:
            mocked = mock.patch(item, **kwargs)
        self._patches[name] = mocked
        started = mocked.start()
        if new is None:
            started.return_value = return_value
        self._patches_start[name] = started
        setattr(self, name, started)


@dataclass
class MockedModule:
    saved_module: Any
    mock: mock.MagicMock


class ModuleMockerTestCase(BaseTestCase):

    # override this in derived classes
    SAVE_MODULES = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_modules: Dict[str, MockedModule] = {}

    def setUp(self):
        for module in self.SAVE_MODULES:
            self._saved_modules[module] = MockedModule(
                sys.modules.get(module, None),
                mock.MagicMock())
            sys.modules[module] = self._saved_modules[module].mock
        super().setUp()

    def tearDown(self):
        for module, dc in self._saved_modules.items():
            if dc.saved_module is not None:
                sys.modules[module] = dc.saved_module
            else:
                del sys.modules[module]
        self._saved_modules = {}
        self.tox_hooks_3 = None  # type:ignore
        super().tearDown()
