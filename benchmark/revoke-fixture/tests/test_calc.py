import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import calc  # noqa: E402


class DivTest(unittest.TestCase):
    def test_div_floors(self):
        self.assertEqual(calc.div(7, 2), 3)

    def test_div_by_zero_returns_none(self):
        self.assertIsNone(calc.div(1, 0))


if __name__ == "__main__":
    unittest.main()
