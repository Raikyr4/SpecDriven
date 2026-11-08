import unittest
from decimal import Decimal

from precos import total


class Total(unittest.TestCase):
    def test_soma(self):
        self.assertEqual(total([10, 5.5]), Decimal("15.5"))


if __name__ == "__main__":
    unittest.main()
