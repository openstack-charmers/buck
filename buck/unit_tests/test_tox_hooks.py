import unittest

from unittest import mock

from buck import tox_hooks

class TestTox(unittest.TestCase):
    def setUp(self):
        self.config = mock.MagicMock()


    def test_get_reader(self):
        tox = tox_hooks.Tox(self.config)
        reader = tox.get_reader('tox')
