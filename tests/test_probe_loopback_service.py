from __future__ import annotations

import unittest

from tools.probe_loopback_service import ProbeConfig


class ProbeConfigTests(unittest.TestCase):
    def test_defaults_are_loopback_only(self) -> None:
        config = ProbeConfig()
        self.assertEqual((config.host, config.port), ("127.0.0.1", 443))

    def test_non_loopback_bind_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "loopback"):
            ProbeConfig(host="0.0.0.0")

    def test_invalid_limits_are_rejected(self) -> None:
        for kwargs in ({"port": 0}, {"max_bytes": 0}, {"read_timeout": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                ProbeConfig(**kwargs)


if __name__ == "__main__":
    unittest.main()
