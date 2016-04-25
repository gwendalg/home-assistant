"""Test the condition helper."""
# pylint: disable=protected-access,too-many-public-methods
import unittest

from homeassistant.helpers import condition

from tests.common import get_test_home_assistant


def test_from_config():
    """Test from config method."""
    condition.from_config({"condition": "zone"})
    assert True
