import unittest

from server.army3_protocol.framing import Packet
from server.army3_protocol.messages import (
    BootstrapE0EmptyResponse,
    ClientPostResetStatus,
    ClientPrelogin72,
    ClientU32B2,
    ClientSessionRequest,
    ClientTransportSync0,
    Command,
    ServerSessionResponse,
    ServerPreloginStatus,
)
from server.session import LoginSession, SessionProtocolError, SessionState


class LoginSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = LoginSession()

    def _complete_handshake(self) -> None:
        outcome = self.session.handle(Packet(Command.HANDSHAKE))
        self.assertIsNotNone(outcome.enable_transform)
        self.assertEqual([packet.command for packet in outcome.outbound], [0xE5])

    def _enter_bootstrap(self) -> None:
        self._complete_handshake()
        outcome = self.session.handle(
            ClientSessionRequest("installation", "config", 1).to_packet()
        )
        self.assertEqual(
            [packet.command for packet in outcome.outbound],
            [Command.CLIENT_SESSION, Command.BOOTSTRAP_VERSIONS],
        )

    def test_requires_e5_as_first_packet(self) -> None:
        with self.assertRaisesRegex(SessionProtocolError, "unexpected command"):
            self.session.handle(Packet(Command.CLIENT_SESSION))

    def test_handshake_advances_state_and_enables_identity_transform(self) -> None:
        outcome = self.session.handle(Packet(Command.HANDSHAKE))
        self.assertEqual(self.session.state, SessionState.AWAIT_INITIAL_BB)
        self.assertEqual(outcome.enable_transform.key, b"\x00")
        self.assertEqual(outcome.enable_transform.shift, 0)

    def test_initial_bb_sends_session_response_then_versions(self) -> None:
        self._enter_bootstrap()
        self.assertEqual(self.session.state, SessionState.BOOTSTRAP)

    def test_experimental_splash_transition_is_sent_once(self) -> None:
        self.session = LoginSession(experimental_splash_revision=127)
        self._complete_handshake()

        initial = self.session.handle(
            ClientSessionRequest("installation", "config", 1).to_packet()
        )
        retry = self.session.handle(
            ClientSessionRequest("installation", "config", 1).to_packet()
        )

        self.assertEqual(
            [packet.command for packet in initial.outbound],
            [
                Command.CLIENT_SESSION,
                Command.BOOTSTRAP_VERSIONS,
                Command.SCREEN_BOOTSTRAP,
            ],
        )
        self.assertEqual(
            [packet.command for packet in retry.outbound],
            [Command.CLIENT_SESSION, Command.BOOTSTRAP_VERSIONS],
        )

    def test_experimental_empty_c4_request_is_accepted_without_response(self) -> None:
        self.session = LoginSession(experimental_splash_revision=127)
        self._complete_handshake()
        self.session.handle(
            ClientSessionRequest("installation", "config", 1).to_packet()
        )

        outcome = self.session.handle(Packet(Command.SCREEN_BOOTSTRAP))

        self.assertEqual(outcome.outbound, ())
        self.assertEqual(self.session.state, SessionState.BOOTSTRAP)

    def test_transport_sync0_is_accepted_before_initial_bb(self) -> None:
        self._complete_handshake()
        outcome = self.session.handle(ClientTransportSync0("local", 0, 0).to_packet())
        self.assertEqual([packet.command for packet in outcome.outbound], [0xA9])
        self.assertEqual(outcome.outbound[0].payload, b"\x02")
        self.assertEqual(self.session.state, SessionState.AWAIT_INITIAL_BB)

        self.session.handle(ClientSessionRequest("installation", "config", 1).to_packet())
        self.assertEqual(self.session.state, SessionState.BOOTSTRAP)

    def test_post_reset_status_is_accepted_before_initial_bb(self) -> None:
        self._complete_handshake()
        self.session.handle(ClientTransportSync0("local", 0, 0).to_packet())

        outcome = self.session.handle(ClientPostResetStatus(0).to_packet())

        self.assertEqual(outcome.outbound, ())
        self.assertEqual(self.session.state, SessionState.AWAIT_INITIAL_BB)

    def test_client_prelogin72_is_accepted_before_initial_bb(self) -> None:
        self._complete_handshake()

        outcome = self.session.handle(ClientPrelogin72(1, 2, "value").to_packet())

        self.assertEqual(outcome.outbound, ())
        self.assertEqual(self.session.state, SessionState.AWAIT_INITIAL_BB)

    def test_prelogin_fd_gets_one_byte_status_response(self) -> None:
        self._complete_handshake()

        outcome = self.session.handle(Packet(Command.PRELOGIN_STATUS))

        self.assertEqual(len(outcome.outbound), 1)
        self.assertEqual(
            ServerPreloginStatus.decode_payload(outcome.outbound[0].payload).value,
            1,
        )
        self.assertEqual(self.session.state, SessionState.AWAIT_INITIAL_BB)

    def test_bootstrap_requests_are_order_independent(self) -> None:
        self._enter_bootstrap()
        commands = (Command.BOOTSTRAP_E1, Command.BOOTSTRAP_DA, Command.BOOTSTRAP_E0)
        responses = []
        for command in commands:
            outcome = self.session.handle(Packet(command))
            responses.append(outcome.outbound[0].command)
        self.assertEqual(responses, list(commands))

    def test_b2_u32_is_accepted_during_bootstrap(self) -> None:
        self._enter_bootstrap()

        outcome = self.session.handle(ClientU32B2(1).to_packet())

        self.assertEqual(outcome.outbound, ())
        self.assertEqual(self.session.state, SessionState.BOOTSTRAP)

    def test_transport_metadata_can_repeat_during_bootstrap(self) -> None:
        self._enter_bootstrap()

        first = self.session.handle(ClientPostResetStatus(0).to_packet())
        second = self.session.handle(ClientPrelogin72(1, 2, "value").to_packet())

        self.assertEqual(first.outbound, ())
        self.assertEqual(second.outbound, ())
        self.assertEqual(self.session.state, SessionState.BOOTSTRAP)

    def test_fd_can_repeat_during_bootstrap(self) -> None:
        self._enter_bootstrap()

        outcome = self.session.handle(Packet(Command.PRELOGIN_STATUS))

        self.assertEqual(outcome.outbound[0].command, Command.PRELOGIN_STATUS)
        self.assertEqual(outcome.outbound[0].payload, b"\x01")
        self.assertEqual(self.session.state, SessionState.BOOTSTRAP)

    def test_bb_retry_during_bootstrap_replays_versions(self) -> None:
        self._enter_bootstrap()

        outcome = self.session.handle(
            ClientSessionRequest("installation", "config", 1).to_packet()
        )

        self.assertEqual(
            [packet.command for packet in outcome.outbound],
            [Command.CLIENT_SESSION, Command.BOOTSTRAP_VERSIONS],
        )
        self.assertEqual(self.session.state, SessionState.BOOTSTRAP)

    def test_db_marks_account_panel_ready(self) -> None:
        self._enter_bootstrap()
        self.session.handle(Packet(Command.BOOTSTRAP_READY))
        self.assertEqual(self.session.state, SessionState.ACCOUNT_PANEL_READY)

        outcome = self.session.handle(
            ClientSessionRequest("not-logged", "not-retained", 0).to_packet()
        )
        response = ServerSessionResponse.decode_payload(outcome.outbound[0].payload)
        self.assertEqual(response.list_for_mode1, "local")

    def test_cache_match_can_reach_ready_without_data_requests(self) -> None:
        self._enter_bootstrap()
        self.session.handle(Packet(Command.UNKNOWN_07))
        self.session.handle(Packet(Command.BOOTSTRAP_READY))
        self.assertEqual(self.session.state, SessionState.ACCOUNT_PANEL_READY)

    def test_nonempty_empty_request_is_rejected(self) -> None:
        self._enter_bootstrap()
        with self.assertRaisesRegex(SessionProtocolError, "empty payload"):
            self.session.handle(Packet(Command.BOOTSTRAP_DA, b"x"))

    def test_invalid_bb_mode_is_rejected(self) -> None:
        self._complete_handshake()
        with self.assertRaisesRegex(SessionProtocolError, "mode"):
            self.session.handle(ClientSessionRequest("a", "b", 2).to_packet())

    def test_ready_state_allows_bootstrap_retry(self) -> None:
        self._enter_bootstrap()
        self.session.handle(Packet(Command.BOOTSTRAP_READY))
        outcome = self.session.handle(Packet(Command.BOOTSTRAP_E0))
        decoded = BootstrapE0EmptyResponse.decode_payload(outcome.outbound[0].payload)
        self.assertEqual(decoded.version, 2)


if __name__ == "__main__":
    unittest.main()
