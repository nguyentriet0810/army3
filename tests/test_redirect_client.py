import hashlib
import shutil
import unittest
from pathlib import Path, PurePosixPath
from uuid import uuid4

from tools.redirect_client import (
    MARKER_NAME,
    PatchPlan,
    RedirectError,
    create_patched_copy,
    load_manifest,
    verify_original_client,
    verify_patched_copy,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RedirectClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / "build" / "test-fixtures" / uuid4().hex
        self.root.mkdir(parents=True)
        self.source = self.root / "source"
        self.build = self.root / "build"
        self.output = self.build / "local-client"
        self.metadata_relative = PurePosixPath("Data/Metadata/global-metadata.dat")
        self.old = b"server.old.1"
        self.new = b"127.000.0.1!"
        self.assertEqual(len(self.old), len(self.new))
        self.original_metadata = b"prefix:" + self.old + b":suffix"
        self.patched_metadata = b"prefix:" + self.new + b":suffix"
        self.plan = PatchPlan(
            metadata_path=self.metadata_relative,
            source_endpoint=self.old,
            target_endpoint=self.new,
            expected_offset=len(b"prefix:"),
            expected_original_sha256=_sha256(self.original_metadata),
            expected_patched_sha256=_sha256(self.patched_metadata),
        )

        metadata = self.source.joinpath(*self.metadata_relative.parts)
        metadata.parent.mkdir(parents=True)
        metadata.write_bytes(self.original_metadata)
        (self.source / "client.exe").write_bytes(b"test executable fixture")
        self.manifest = self.root / "hashes.sha256"
        self.manifest.write_text(
            f"{_sha256(b'test executable fixture')} *client.exe\n"
            f"{_sha256(self.original_metadata)} *{self.metadata_relative.as_posix()}\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)

    def test_create_copy_patches_only_output_and_verifies_both_trees(self) -> None:
        create_patched_copy(
            self.source,
            self.output,
            self.manifest,
            self.plan,
            allowed_output_root=self.build,
        )

        source_metadata = self.source.joinpath(*self.metadata_relative.parts)
        output_metadata = self.output.joinpath(*self.metadata_relative.parts)
        self.assertEqual(source_metadata.read_bytes(), self.original_metadata)
        self.assertEqual(output_metadata.read_bytes(), self.patched_metadata)
        self.assertTrue((self.output / MARKER_NAME).is_file())

        verify_original_client(
            self.source,
            load_manifest(self.manifest),
            self.plan,
        )
        verify_patched_copy(
            self.output,
            self.manifest,
            self.plan,
            allowed_output_root=self.build,
        )

    def test_existing_output_is_never_overwritten(self) -> None:
        self.output.mkdir(parents=True)
        sentinel = self.output / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(RedirectError, "refusing to overwrite"):
            create_patched_copy(
                self.source,
                self.output,
                self.manifest,
                self.plan,
                allowed_output_root=self.build,
            )
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_output_outside_allowed_build_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(RedirectError, "must be a child"):
            create_patched_copy(
                self.source,
                self.root / "outside",
                self.manifest,
                self.plan,
                allowed_output_root=self.build,
            )

    def test_wrong_source_hash_is_rejected_before_copy(self) -> None:
        (self.source / "client.exe").write_bytes(b"tampered")
        with self.assertRaisesRegex(RedirectError, "hash mismatch"):
            create_patched_copy(
                self.source,
                self.output,
                self.manifest,
                self.plan,
                allowed_output_root=self.build,
            )
        self.assertFalse(self.output.exists())

    def test_file_outside_manifest_is_rejected(self) -> None:
        (self.source / "unexpected.exe").write_bytes(b"unexpected")
        with self.assertRaisesRegex(RedirectError, "outside the manifest"):
            create_patched_copy(
                self.source,
                self.output,
                self.manifest,
                self.plan,
                allowed_output_root=self.build,
            )
        self.assertFalse(self.output.exists())

    def test_multiple_endpoint_occurrences_are_rejected(self) -> None:
        metadata = self.source.joinpath(*self.metadata_relative.parts)
        repeated = b"prefix:" + self.old + b":" + self.old
        metadata.write_bytes(repeated)
        repeated_plan = PatchPlan(
            metadata_path=self.metadata_relative,
            source_endpoint=self.old,
            target_endpoint=self.new,
            expected_offset=len(b"prefix:"),
            expected_original_sha256=_sha256(repeated),
            expected_patched_sha256=_sha256(repeated.replace(self.old, self.new)),
        )
        entries = load_manifest(self.manifest)
        entries[self.metadata_relative] = _sha256(repeated)
        with self.assertRaisesRegex(RedirectError, "occurrence count"):
            verify_original_client(self.source, entries, repeated_plan)

    def test_tampered_patched_copy_is_detected(self) -> None:
        create_patched_copy(
            self.source,
            self.output,
            self.manifest,
            self.plan,
            allowed_output_root=self.build,
        )
        (self.output / "client.exe").write_bytes(b"tampered")
        with self.assertRaisesRegex(RedirectError, "hash mismatch"):
            verify_patched_copy(
                self.output,
                self.manifest,
                self.plan,
                allowed_output_root=self.build,
            )

    def test_unsafe_manifest_path_is_rejected(self) -> None:
        self.manifest.write_text(f"{'0' * 64} *../outside\n", encoding="utf-8")
        with self.assertRaisesRegex(RedirectError, "unsafe manifest path"):
            load_manifest(self.manifest)


if __name__ == "__main__":
    unittest.main()
