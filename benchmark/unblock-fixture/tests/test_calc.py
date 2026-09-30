import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import calc  # noqa: E402


class ModuleTest(unittest.TestCase):
    def test_module_imports(self):
        self.assertTrue(calc.__doc__)


if __name__ == "__main__":
    unittest.main()
