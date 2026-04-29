"""Tests for the top-level get_port wrapper script."""

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class GetPortTests(unittest.TestCase):
    """Validate wrapper output contract for get_port.py."""

    def test_wrapper_prints_ip_and_port(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "get_port.py")],
            check=True,
            capture_output=True,
            text=True,
        )

        output = result.stdout.strip()
        parts = output.split()
        self.assertEqual(len(parts), 2)

        ip, port = parts
        self.assertTrue(ip)
        self.assertGreater(int(port), 0)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
