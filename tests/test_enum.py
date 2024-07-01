from enum import Enum
from unittest import TestCase

from baumbelt.enums import EnumContainsMeta


class AtomEnum(Enum, metaclass=EnumContainsMeta):
    hydrogen = 1
    helium = 2
    lithium = 3
    neon = 10


class EnumContainsTestCase(TestCase):

    def test_enum_contains(self):
        self.assertIn("hydrogen", AtomEnum)
        self.assertIn("helium", AtomEnum)
        self.assertIn("lithium", AtomEnum)
        self.assertIn("neon", AtomEnum)
        self.assertNotIn("water", AtomEnum)
