import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import tags  # noqa: E402


class UniqueTagsTest(unittest.TestCase):
    def test_distinct_and_alphabetical(self):
        self.assertEqual(tags.unique_tags(["b", "a", "b"]), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
