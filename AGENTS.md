# AGENTS.md

## Project goal

This is an educational client-server research project. The goal is to build a
local, offline-compatible environment for the Army3 client so it can be played
privately without depending on a third-party game server.

The project is not intended to operate a public game service, bypass payments,
or redistribute proprietary game assets.

## Repository scope

- Treat `Mobiarmy3HA_3.0.0_GOC/` as read-only reference material.
- Never edit, rename, delete, or commit files from the original client folder.
- Keep original binaries and assets out of Git.
- Store reproducible source code, tools, notes, schemas, and tests in Git.
- Keep generated dumps, extracted assets, logs, captures, and builds out of Git
  unless a small fixture is deliberately required for a test.

## Safety and network rules

- Do not run the supplied client or any unknown binary without explicit user
  approval.
- Prefer static analysis before dynamic analysis.
- Dynamic analysis must use an isolated environment with outbound network
  access blocked by default.
- A local compatibility server must listen on loopback (`127.0.0.1`) by default.
- Do not contact, probe, modify, or disrupt any third-party game server.
- Never commit credentials, tokens, account data, machine-specific secrets, or
  personally identifiable information.

## Engineering approach

Work in small, verifiable milestones:

1. Inventory the Unity IL2CPP client and record hashes and versions.
2. Recover useful metadata, types, and networking entry points.
3. Document the wire protocol and message lifecycle with evidence.
4. Implement a minimal local server for connection and login.
5. Add character state, rooms, maps, and match behavior incrementally.
6. Add offline persistence and optional bots only after the core protocol works.

Do not claim protocol behavior from names or guesses alone. Mark findings as one
of: `confirmed`, `inferred`, or `unknown`, and record the supporting evidence.

## Suggested layout

Use this layout as components are introduced:

```text
analysis/       Human-written findings, protocol notes, and inventories
docs/           Architecture and user-facing documentation
server/         Offline compatibility server source
tools/          Reproducible analysis and conversion utilities
tests/          Automated tests and small legal test fixtures
scripts/        Development and launch scripts
```

Create directories only when they have real content. Generated output belongs
under ignored paths such as `analysis/generated/`, `analysis/dumps/`, `build/`,
`dist/`, `logs/`, or `tmp/`.

## Code quality

- Prefer clear, maintainable code over clever reverse-engineering shortcuts.
- Keep protocol parsing separate from game/domain logic and persistence.
- Validate all packet lengths, identifiers, and state transitions.
- Bind services to configurable addresses and ports; default to loopback.
- Make local data deterministic and easy to reset.
- Add tests for packet codecs and every confirmed protocol behavior.
- Document non-obvious binary formats, constants, and compatibility decisions.

## Verification

Before considering a change complete:

- Run relevant formatters, linters, and tests.
- Confirm no original client files or generated dumps are staged.
- Confirm no service unintentionally listens on a public interface.
- Summarize what was verified and what remains inferred or untested.

## Git workflow

- Keep commits focused and use descriptive commit messages.
- Do not commit the original client, proprietary asset archives, generated
  reverse-engineering output, secrets, or large binaries.
- Do not rewrite published history or force-push unless the user explicitly asks.
- Do not push changes unless the user explicitly requests a push.
- Prefer a feature branch and pull request for substantial changes; small setup
  changes may go directly to `main` when the user requests it.

## Communication

- Use Vietnamese when communicating with the user unless requested otherwise.
- Explain uncertainty and tradeoffs directly.
- Ask before any action that runs untrusted code, enables external network
  access, or changes/removes original client data.
