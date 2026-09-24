# M2: Cpp2IL smoke test

Status: partial M2 evidence; no protocol behavior confirmed.

## Inputs and tool

- Client: `Mobiarmy3HA_3.0.0_GOC/` (read-only reference).
- Tool: Cpp2IL Windows x64 development CI build, version
  `2022.1.0-development.1715+f92ff8b`.
- Tool SHA-256: `7AFC9A908014483BBFB847E2A06C90231EA0318899C6215B9DB3A2C105E9C38D`.
- Local tool and generated output: `tmp/cpp2il/` (Git-ignored).

## Run

Command arguments: `--game-path=D:\hs_army3\Mobiarmy3HA_3.0.0_GOC`,
`--exe-name=Mobi Army 3 HA`, `--output-as=dll_empty`, and
`--output-to=D:\hs_army3\tmp\cpp2il\out`.

Confirmed from Cpp2IL output:

- Detected Unity `6000.5.10f1`.
- Parsed IL2CPP metadata using internal layout version `106` for the file's
  version `107` header.
- Located code registration at `0x1811E3870` and metadata registration at
  `0x181251610` in `GameAssembly.dll`.
- Mapped 45,467 method definitions.
- Produced 80 generated DLLs totaling 6,916,608 bytes, including
  `Assembly-CSharp.dll`.
- Exit code `0`; total reported execution time about 2.8 seconds.
- SHA-256 of original `GameAssembly.dll` and `global-metadata.dat` still matches
  the M1 manifest after the run.

These are structural DLLs with empty method bodies, not recovered server code or
complete client C# source. No client executable was run, and no third-party
server was contacted. Networking entry points and packet behavior remain unknown.
