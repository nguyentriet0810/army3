"""Pure per-connection state machine for the minimal local-login path."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .army3_protocol.errors import DecodeError, ProtocolError
from .army3_protocol.framing import Packet
from .army3_protocol.messages import (
    BootstrapDaResponse,
    BootstrapE0EmptyResponse,
    BootstrapE1Response,
    BootstrapVersions,
    ClientPostResetStatus,
    ClientSessionRequest,
    ClientPrelogin72,
    ClientU32B2,
    ClientTransportSync0,
    Command,
    EmptyClientRequest,
    HandshakeResponse,
    ServerSessionResponse,
    ServerPreloginStatus,
    ServerTransportReset2,
    ScreenBootstrapResponse,
)
from .army3_protocol.transform import ByteTransform


class SessionProtocolError(ProtocolError):
    """A packet is structurally valid but illegal in the current state."""


class SessionState(Enum):
    AWAIT_CLIENT_E5 = auto()
    AWAIT_INITIAL_BB = auto()
    BOOTSTRAP = auto()
    ACCOUNT_PANEL_READY = auto()


@dataclass(frozen=True, slots=True)
class SessionOutcome:
    outbound: tuple[Packet, ...] = ()
    enable_transform: ByteTransform | None = None


class LoginSession:
    """No-auth compatibility state machine; it never retains submitted text."""

    _SEED = b"\x00"
    _SHIFT = 0
    _LOCAL_TEXT = "local"
    # Version 1 is already present in the runtime cache created by earlier
    # experiments.  Bumping the deterministic local fixture forces the real
    # client through all three confirmed cache-response handlers at least
    # once, instead of relying on the still-unverified cache-hit path.
    _VERSION = 2

    def __init__(self, experimental_splash_revision: int | None = None) -> None:
        self._state = SessionState.AWAIT_CLIENT_E5
        self._experimental_splash_revision = experimental_splash_revision
        self._splash_transition_sent = False

    @property
    def state(self) -> SessionState:
        return self._state

    def handle(self, packet: Packet) -> SessionOutcome:
        if self._state is SessionState.AWAIT_CLIENT_E5:
            return self._handle_e5(packet)
        if self._state is SessionState.AWAIT_INITIAL_BB:
            return self._handle_initial_bb(packet)
        if self._state is SessionState.BOOTSTRAP:
            return self._handle_bootstrap(packet)
        return self._handle_ready(packet)

    def _handle_e5(self, packet: Packet) -> SessionOutcome:
        self._decode_empty(packet, Command.HANDSHAKE)
        transform = ByteTransform.from_seed(self._SEED, self._SHIFT)
        response = HandshakeResponse(self._SEED, self._SHIFT, self._LOCAL_TEXT)
        self._state = SessionState.AWAIT_INITIAL_BB
        return SessionOutcome((response.to_packet(),), transform)

    def _handle_initial_bb(self, packet: Packet) -> SessionOutcome:
        if packet.command == Command.TRANSPORT_SYNC:
            self._decode_transport_sync(packet)
            return SessionOutcome((ServerTransportReset2().to_packet(),))
        if packet.command == Command.POST_RESET_STATUS:
            self._decode_post_reset_status(packet)
            return SessionOutcome()
        if packet.command == Command.CLIENT_TEXT_72:
            self._decode_client_prelogin72(packet)
            return SessionOutcome()
        if packet.command == Command.PRELOGIN_STATUS:
            self._decode_empty(packet, Command.PRELOGIN_STATUS)
            return SessionOutcome((ServerPreloginStatus().to_packet(),))
        self._decode_session_request(packet)
        self._state = SessionState.BOOTSTRAP
        return SessionOutcome(self._initial_bootstrap_responses())

    def _handle_bootstrap(self, packet: Packet) -> SessionOutcome:
        command = packet.command
        if command == Command.POST_RESET_STATUS:
            self._decode_post_reset_status(packet)
            return SessionOutcome()
        if command == Command.CLIENT_TEXT_72:
            self._decode_client_prelogin72(packet)
            return SessionOutcome()
        if command == Command.PRELOGIN_STATUS:
            self._decode_empty(packet, Command.PRELOGIN_STATUS)
            return SessionOutcome((ServerPreloginStatus().to_packet(),))
        if command == Command.CLIENT_SESSION:
            self._decode_session_request(packet)
            # Runtime observation: the Windows client can send a second 0xBB
            # after its 0x3A/0x72/0xFD prelogin sequence. That sequence resets
            # bootstrap state, so replay the version barrier after the 0xBB
            # response instead of assuming the first 0xE2 is still effective.
            return SessionOutcome(self._initial_bootstrap_responses())
        if command == Command.SCREEN_BOOTSTRAP:
            self._decode_experimental_screen_request(packet)
            return SessionOutcome()
        if command == Command.CLIENT_U32_B2:
            self._decode_client_u32_b2(packet)
            return SessionOutcome()
        if command == Command.UNKNOWN_07:
            self._decode_empty(packet, Command.UNKNOWN_07)
            return SessionOutcome()
        if command == Command.BOOTSTRAP_DA:
            self._decode_empty(packet, Command.BOOTSTRAP_DA)
            return SessionOutcome((BootstrapDaResponse.empty(self._VERSION).to_packet(),))
        if command == Command.BOOTSTRAP_E1:
            self._decode_empty(packet, Command.BOOTSTRAP_E1)
            return SessionOutcome((BootstrapE1Response.empty(self._VERSION).to_packet(),))
        if command == Command.BOOTSTRAP_E0:
            self._decode_empty(packet, Command.BOOTSTRAP_E0)
            return SessionOutcome(
                (BootstrapE0EmptyResponse(self._VERSION).to_packet(),)
            )
        if command == Command.BOOTSTRAP_READY:
            self._decode_empty(packet, Command.BOOTSTRAP_READY)
            self._state = SessionState.ACCOUNT_PANEL_READY
            return SessionOutcome()
        self._raise_unexpected(packet)

    def _handle_ready(self, packet: Packet) -> SessionOutcome:
        command = packet.command
        if command == Command.POST_RESET_STATUS:
            self._decode_post_reset_status(packet)
            return SessionOutcome()
        if command == Command.CLIENT_TEXT_72:
            self._decode_client_prelogin72(packet)
            return SessionOutcome()
        if command == Command.PRELOGIN_STATUS:
            self._decode_empty(packet, Command.PRELOGIN_STATUS)
            return SessionOutcome((ServerPreloginStatus().to_packet(),))
        if command == Command.CLIENT_SESSION:
            self._decode_session_request(packet)
            return SessionOutcome((self._session_response().to_packet(),))
        if command == Command.SCREEN_BOOTSTRAP:
            self._decode_experimental_screen_request(packet)
            return SessionOutcome()
        if command in {Command.UNKNOWN_07, Command.BOOTSTRAP_READY}:
            self._decode_empty(packet, Command(command))
            return SessionOutcome()
        if command in {
            Command.BOOTSTRAP_DA,
            Command.BOOTSTRAP_E1,
            Command.BOOTSTRAP_E0,
        }:
            return self._handle_bootstrap_retry(packet)
        self._raise_unexpected(packet)

    def _handle_bootstrap_retry(self, packet: Packet) -> SessionOutcome:
        # Retry responses are harmless and make reconnect/cache races deterministic.
        command = Command(packet.command)
        self._decode_empty(packet, command)
        if command is Command.BOOTSTRAP_DA:
            response = BootstrapDaResponse.empty(self._VERSION).to_packet()
        elif command is Command.BOOTSTRAP_E1:
            response = BootstrapE1Response.empty(self._VERSION).to_packet()
        else:
            response = BootstrapE0EmptyResponse(self._VERSION).to_packet()
        return SessionOutcome((response,))

    def _decode_session_request(self, packet: Packet) -> ClientSessionRequest:
        if packet.command != Command.CLIENT_SESSION:
            self._raise_unexpected(packet)
        try:
            request = ClientSessionRequest.decode_payload(packet.payload)
        except DecodeError as exc:
            raise SessionProtocolError("invalid 0xBB payload") from exc
        if request.mode not in {0, 1}:
            raise SessionProtocolError("0xBB mode must be 0 or 1")
        return request

    def _decode_transport_sync(self, packet: Packet) -> ClientTransportSync0:
        try:
            return ClientTransportSync0.decode_payload(packet.payload)
        except DecodeError as exc:
            raise SessionProtocolError("invalid client 0xA9/0 payload") from exc

    def _decode_post_reset_status(self, packet: Packet) -> ClientPostResetStatus:
        try:
            return ClientPostResetStatus.decode_payload(packet.payload)
        except DecodeError as exc:
            raise SessionProtocolError("invalid client 0x3A payload") from exc

    def _decode_client_prelogin72(self, packet: Packet) -> ClientPrelogin72:
        try:
            return ClientPrelogin72.decode_payload(packet.payload)
        except DecodeError as exc:
            raise SessionProtocolError("invalid client 0x72 payload") from exc

    def _decode_client_u32_b2(self, packet: Packet) -> ClientU32B2:
        try:
            return ClientU32B2.decode_payload(packet.payload)
        except DecodeError as exc:
            raise SessionProtocolError("invalid client 0xB2 payload") from exc

    def _decode_empty(self, packet: Packet, command: Command) -> None:
        if packet.command != command:
            self._raise_unexpected(packet)
        try:
            EmptyClientRequest.from_packet(packet)
        except DecodeError as exc:
            raise SessionProtocolError(
                f"command 0x{packet.command:02X} must have an empty payload"
            ) from exc

    def _session_response(self) -> ServerSessionResponse:
        return ServerSessionResponse(
            self._LOCAL_TEXT,
            self._LOCAL_TEXT,
            self._LOCAL_TEXT,
            self._LOCAL_TEXT,
        )

    def _initial_bootstrap_responses(self) -> tuple[Packet, ...]:
        responses = [
            self._session_response().to_packet(),
            BootstrapVersions(
                self._VERSION,
                self._VERSION,
                self._VERSION,
            ).to_packet(),
        ]
        if (
            self._experimental_splash_revision is not None
            and not self._splash_transition_sent
        ):
            responses.append(
                ScreenBootstrapResponse(
                    self._experimental_splash_revision
                ).to_packet()
            )
            self._splash_transition_sent = True
        return tuple(responses)

    def _decode_experimental_screen_request(self, packet: Packet) -> None:
        if self._experimental_splash_revision is None:
            self._raise_unexpected(packet)
        self._decode_empty(packet, Command.SCREEN_BOOTSTRAP)

    def _raise_unexpected(self, packet: Packet) -> None:
        raise SessionProtocolError(
            f"unexpected command 0x{packet.command:02X} in state {self._state.name}"
        )
