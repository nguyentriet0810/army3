"""Create and verify an ignored Army3 client copy redirected to loopback."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import NoReturn
from uuid import uuid4


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPOSITORY_ROOT / "Mobiarmy3HA_3.0.0_GOC"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "build" / "army3-local-client"
DEFAULT_MANIFEST = REPOSITORY_ROOT / "analysis" / "hashes.sha256"
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / "build"
MARKER_NAME = ".army3-local-copy.json"


class RedirectError(RuntimeError):
    """A safety or verification condition prevented client redirection."""


@dataclass(frozen=True, slots=True)
class PatchPlan:
    metadata_path: PurePosixPath
    source_endpoint: bytes
    target_endpoint: bytes
    expected_offset: int
    expected_original_sha256: str
    expected_patched_sha256: str

    def __post_init__(self) -> None:
        if self.metadata_path.is_absolute() or ".." in self.metadata_path.parts:
            raise ValueError("metadata_path must be a safe relative path")
        if len(self.source_endpoint) != len(self.target_endpoint):
            raise ValueError("source and target endpoints must have equal byte length")
        if not self.source_endpoint:
            raise ValueError("endpoint bytes must not be empty")
        if self.expected_offset < 0:
            raise ValueError("expected_offset must be non-negative")
        for name, value in (
            ("expected_original_sha256", self.expected_original_sha256),
            ("expected_patched_sha256", self.expected_patched_sha256),
        ):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValueError(f"{name} must be a lowercase SHA-256 value")


DEFAULT_PATCH = PatchPlan(
    metadata_path=PurePosixPath(
        "Mobi Army 3 HA_Data/il2cpp_data/Metadata/global-metadata.dat"
    ),
    source_endpoint=b"14.225.206.44",
    target_endpoint=b"127.000.000.1",
    expected_offset=6_469_992,
    expected_original_sha256=(
        "0debeea2cb8aa5013709f7845d1bba21800d6974b1461be8482d3558d43775c9"
    ),
    expected_patched_sha256=(
        "b4890d59779968d8a544f3dfb3a75778da948e61d590ae9d1631b7a132b85cf4"
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[PurePosixPath, str]:
    entries: dict[PurePosixPath, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RedirectError(f"cannot read manifest: {path}") from exc

    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            digest, raw_relative = line.split(maxsplit=1)
        except ValueError as exc:
            raise RedirectError(f"invalid manifest line {line_number}") from exc
        if raw_relative.startswith("*"):
            raw_relative = raw_relative[1:]
        relative = PurePosixPath(raw_relative)
        if relative.is_absolute() or ".." in relative.parts:
            raise RedirectError(f"unsafe manifest path at line {line_number}")
        digest = digest.lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise RedirectError(f"invalid SHA-256 at manifest line {line_number}")
        if relative in entries:
            raise RedirectError(f"duplicate manifest path: {relative}")
        entries[relative] = digest

    if not entries:
        raise RedirectError("manifest is empty")
    return entries


def _native_path(root: Path, relative: PurePosixPath) -> Path:
    return root.joinpath(*relative.parts)


def _find_unexpected_files(
    root: Path,
    manifest: dict[PurePosixPath, str],
    *,
    allowed_extra: frozenset[PurePosixPath] = frozenset(),
) -> list[PurePosixPath]:
    expected = set(manifest) | set(allowed_extra)
    actual = {
        PurePosixPath(path.relative_to(root).as_posix())
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    return sorted(actual - expected, key=str)


def verify_original_client(
    source: Path,
    manifest: dict[PurePosixPath, str],
    plan: PatchPlan = DEFAULT_PATCH,
) -> None:
    source = source.resolve()
    if not source.is_dir():
        raise RedirectError(f"client source directory does not exist: {source}")
    if plan.metadata_path not in manifest:
        raise RedirectError("metadata file is missing from the manifest")
    if manifest[plan.metadata_path] != plan.expected_original_sha256:
        raise RedirectError("manifest metadata hash does not match the patch plan")

    failures: list[str] = []
    for relative, expected_hash in manifest.items():
        path = _native_path(source, relative)
        if path.is_symlink():
            failures.append(f"symlink is not allowed: {relative}")
        elif not path.is_file():
            failures.append(f"missing file: {relative}")
        else:
            actual_hash = sha256_file(path)
            if actual_hash != expected_hash:
                failures.append(f"hash mismatch: {relative}")
        if len(failures) >= 10:
            break
    if failures:
        raise RedirectError("client verification failed: " + "; ".join(failures))
    unexpected = _find_unexpected_files(source, manifest)
    if unexpected:
        names = ", ".join(str(path) for path in unexpected[:10])
        raise RedirectError(f"client contains files outside the manifest: {names}")

    _verify_metadata_bytes(
        _native_path(source, plan.metadata_path),
        plan,
        expected_hash=plan.expected_original_sha256,
        source_count=1,
        target_count=0,
    )


def _verify_metadata_bytes(
    path: Path,
    plan: PatchPlan,
    *,
    expected_hash: str,
    source_count: int,
    target_count: int,
) -> None:
    data = path.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_hash != expected_hash:
        raise RedirectError(f"metadata hash mismatch: {path}")
    if data.count(plan.source_endpoint) != source_count:
        raise RedirectError("unexpected source endpoint occurrence count")
    if data.count(plan.target_endpoint) != target_count:
        raise RedirectError("unexpected target endpoint occurrence count")
    expected_bytes = (
        plan.source_endpoint if source_count == 1 else plan.target_endpoint
    )
    if data[plan.expected_offset : plan.expected_offset + len(expected_bytes)] != expected_bytes:
        raise RedirectError("endpoint does not occur at the expected metadata offset")


def _ensure_output_is_safe(output: Path, allowed_output_root: Path) -> tuple[Path, Path]:
    output = output.resolve()
    allowed_output_root = allowed_output_root.resolve()
    if output == allowed_output_root or allowed_output_root not in output.parents:
        raise RedirectError(f"output must be a child of {allowed_output_root}")
    return output, allowed_output_root


def _patch_metadata(path: Path, plan: PatchPlan) -> None:
    _verify_metadata_bytes(
        path,
        plan,
        expected_hash=plan.expected_original_sha256,
        source_count=1,
        target_count=0,
    )
    with path.open("r+b") as stream:
        stream.seek(plan.expected_offset)
        current = stream.read(len(plan.source_endpoint))
        if current != plan.source_endpoint:
            raise RedirectError("metadata changed before patch write")
        stream.seek(plan.expected_offset)
        stream.write(plan.target_endpoint)
        stream.flush()
        os.fsync(stream.fileno())
    _verify_metadata_bytes(
        path,
        plan,
        expected_hash=plan.expected_patched_sha256,
        source_count=0,
        target_count=1,
    )


def _marker_payload(manifest_path: Path, plan: PatchPlan) -> dict[str, object]:
    return {
        "schema": 1,
        "manifest_sha256": sha256_file(manifest_path),
        "metadata_path": plan.metadata_path.as_posix(),
        "offset": plan.expected_offset,
        "source_endpoint": plan.source_endpoint.decode("ascii"),
        "target_endpoint": plan.target_endpoint.decode("ascii"),
        "original_metadata_sha256": plan.expected_original_sha256,
        "patched_metadata_sha256": plan.expected_patched_sha256,
        "server_port": 19150,
    }


def verify_patched_copy(
    output: Path,
    manifest_path: Path,
    plan: PatchPlan = DEFAULT_PATCH,
    *,
    allowed_output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> None:
    output, _ = _ensure_output_is_safe(output, allowed_output_root)
    if not output.is_dir():
        raise RedirectError(f"patched client directory does not exist: {output}")
    manifest = load_manifest(manifest_path)
    marker_path = output / MARKER_NAME
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RedirectError(f"invalid or missing marker: {marker_path}") from exc
    if marker != _marker_payload(manifest_path, plan):
        raise RedirectError("patched-copy marker does not match this tool and manifest")

    failures: list[str] = []
    for relative, original_hash in manifest.items():
        path = _native_path(output, relative)
        expected_hash = (
            plan.expected_patched_sha256
            if relative == plan.metadata_path
            else original_hash
        )
        if path.is_symlink():
            failures.append(f"symlink is not allowed: {relative}")
        elif not path.is_file():
            failures.append(f"missing file: {relative}")
        elif sha256_file(path) != expected_hash:
            failures.append(f"hash mismatch: {relative}")
        if len(failures) >= 10:
            break
    if failures:
        raise RedirectError("patched-copy verification failed: " + "; ".join(failures))
    unexpected = _find_unexpected_files(
        output,
        manifest,
        allowed_extra=frozenset({PurePosixPath(MARKER_NAME)}),
    )
    if unexpected:
        names = ", ".join(str(path) for path in unexpected[:10])
        raise RedirectError(f"patched copy contains files outside the manifest: {names}")

    _verify_metadata_bytes(
        _native_path(output, plan.metadata_path),
        plan,
        expected_hash=plan.expected_patched_sha256,
        source_count=0,
        target_count=1,
    )


def create_patched_copy(
    source: Path,
    output: Path,
    manifest_path: Path,
    plan: PatchPlan = DEFAULT_PATCH,
    *,
    allowed_output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> None:
    source = source.resolve()
    output, allowed_output_root = _ensure_output_is_safe(output, allowed_output_root)
    manifest_path = manifest_path.resolve()
    if source == output or source in output.parents:
        raise RedirectError("output must not be inside the original client directory")
    if output.exists():
        raise RedirectError(f"output already exists; refusing to overwrite: {output}")

    manifest = load_manifest(manifest_path)
    verify_original_client(source, manifest, plan)
    allowed_output_root.mkdir(parents=True, exist_ok=True)
    temporary = allowed_output_root / f".{output.name}.tmp-{uuid4().hex}"
    if temporary.exists():
        raise RedirectError(f"temporary output unexpectedly exists: {temporary}")

    published = False
    try:
        shutil.copytree(source, temporary, copy_function=shutil.copy2)
        _patch_metadata(_native_path(temporary, plan.metadata_path), plan)
        marker = _marker_payload(manifest_path, plan)
        (temporary / MARKER_NAME).write_text(
            json.dumps(marker, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        verify_patched_copy(
            temporary,
            manifest_path,
            plan,
            allowed_output_root=allowed_output_root,
        )
        temporary.rename(output)
        published = True
        verify_patched_copy(
            output,
            manifest_path,
            plan,
            allowed_output_root=allowed_output_root,
        )
        verify_original_client(source, manifest, plan)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        if published and output.exists():
            shutil.rmtree(output)
        raise


def _path_argument(value: str) -> Path:
    return Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or verify an ignored Army3 localhost client copy"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_source = subparsers.add_parser("verify-source")
    verify_source.add_argument("--source", type=_path_argument, default=DEFAULT_SOURCE)
    verify_source.add_argument(
        "--manifest", type=_path_argument, default=DEFAULT_MANIFEST
    )

    create = subparsers.add_parser("create")
    create.add_argument("--source", type=_path_argument, default=DEFAULT_SOURCE)
    create.add_argument("--output", type=_path_argument, default=DEFAULT_OUTPUT)
    create.add_argument("--manifest", type=_path_argument, default=DEFAULT_MANIFEST)

    verify_copy = subparsers.add_parser("verify-copy")
    verify_copy.add_argument("--output", type=_path_argument, default=DEFAULT_OUTPUT)
    verify_copy.add_argument(
        "--manifest", type=_path_argument, default=DEFAULT_MANIFEST
    )
    return parser


def _fail(parser: argparse.ArgumentParser, message: str) -> NoReturn:
    parser.error(message)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-source":
            manifest = load_manifest(args.manifest)
            verify_original_client(args.source, manifest)
            print(f"verified original client: {args.source.resolve()}")
        elif args.command == "create":
            create_patched_copy(args.source, args.output, args.manifest)
            print(f"created verified localhost client copy: {args.output.resolve()}")
        else:
            verify_patched_copy(args.output, args.manifest)
            print(f"verified localhost client copy: {args.output.resolve()}")
    except RedirectError as exc:
        _fail(parser, str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
