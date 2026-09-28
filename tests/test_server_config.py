import unittest

from server.config import ServerConfig


class ServerConfigTests(unittest.TestCase):
    def test_default_is_expected_loopback_endpoint(self) -> None:
        config = ServerConfig()
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 19150)
        self.assertEqual(config.heartbeat_interval_seconds, 10.0)

    def test_ipv4_and_ipv6_loopback_are_allowed(self) -> None:
        self.assertEqual(ServerConfig(host="127.0.0.2").host, "127.0.0.2")
        self.assertEqual(ServerConfig(host="::1").host, "::1")

    def test_public_or_unspecified_bind_is_rejected(self) -> None:
        for host in ("0.0.0.0", "192.168.1.20", "8.8.8.8", "::"):
            with self.subTest(host=host), self.assertRaisesRegex(
                ValueError, "loopback"
            ):
                ServerConfig(host=host)

    def test_hostname_is_rejected_to_avoid_ambiguous_resolution(self) -> None:
        with self.assertRaisesRegex(ValueError, "numeric loopback"):
            ServerConfig(host="localhost")

    def test_invalid_port_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ServerConfig(port=-1)
        with self.assertRaises(ValueError):
            ServerConfig(port=65536)

    def test_invalid_heartbeat_interval_is_rejected(self) -> None:
        for value in (0, 0.09, 301, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ServerConfig(heartbeat_interval_seconds=value)


if __name__ == "__main__":
    unittest.main()
