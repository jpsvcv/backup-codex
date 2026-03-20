"""Regression tests for backup, verification and restore flows."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from codex_backup.core import (
    BackupIntegrityError,
    collect_entries,
    create_backup,
    restore_backup,
    verify_backup,
)


def build_sample_codex_home(root: Path) -> Path:
    """Create a small synthetic Codex home used by the test suite."""

    codex_home = root / ".codex"
    (codex_home / "sessions" / "2026" / "03" / "20").mkdir(parents=True, exist_ok=True)
    (codex_home / "tmp").mkdir(parents=True, exist_ok=True)
    (codex_home / ".sandbox").mkdir(parents=True, exist_ok=True)
    (codex_home / "skills" / ".system").mkdir(parents=True, exist_ok=True)
    (codex_home / "sessions" / "2026" / "03" / "20" / "rollout.jsonl").write_text(
        '{"type":"message"}\n',
        encoding="utf-8",
    )
    (codex_home / "config.toml").write_text('model = "gpt-5.4"\n', encoding="utf-8")
    (codex_home / "auth.json").write_text('{"token":"secret"}\n', encoding="utf-8")
    (codex_home / "cap_sid").write_text("session-cookie", encoding="utf-8")
    (codex_home / "tmp" / "scratch.txt").write_text("temporary", encoding="utf-8")
    (codex_home / ".sandbox" / "sandbox.log").write_text("sandbox", encoding="utf-8")

    database_path = codex_home / "state_1.sqlite"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY, body TEXT)")
        connection.execute("INSERT INTO messages(body) VALUES (?)", ("hello backup",))
        connection.commit()
    finally:
        connection.close()

    return codex_home


class BackupFlowTests(unittest.TestCase):
    def test_collect_entries_portable_excludes_runtime_and_optional_secrets(self) -> None:
        """Portable mode should skip transient runtime files and optional secrets."""

        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = build_sample_codex_home(Path(temp_dir))
            entries = collect_entries(codex_home, mode="portable", include_secrets=False)
            relative_paths = {entry.relative_path for entry in entries}

            self.assertIn("config.toml", relative_paths)
            self.assertNotIn("auth.json", relative_paths)
            self.assertNotIn("tmp/scratch.txt", relative_paths)
            self.assertNotIn(".sandbox/sandbox.log", relative_paths)

    def test_directory_backup_and_restore_preserve_sqlite_content(self) -> None:
        """A directory backup should round-trip file content and SQLite state."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            codex_home = build_sample_codex_home(root)
            destination = root / "backup-dir"
            manifest = create_backup(codex_home, destination, force=True)

            restored_home = root / "restored-home"
            restore_backup(destination, restored_home, force=True)

            self.assertEqual(manifest.summary["sqlite_databases"], 1)
            self.assertTrue((restored_home / "auth.json").exists())
            self.assertFalse((restored_home / "tmp" / "scratch.txt").exists())

            restored_db = sqlite3.connect(restored_home / "state_1.sqlite")
            try:
                body = restored_db.execute("SELECT body FROM messages").fetchone()[0]
            finally:
                restored_db.close()
            self.assertEqual(body, "hello backup")

    def test_zip_backup_and_restore_can_skip_secrets(self) -> None:
        """A restore can intentionally omit credential files from the payload."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            codex_home = build_sample_codex_home(root)
            destination = root / "backup.zip"
            create_backup(codex_home, destination, force=True)

            restored_home = root / "restored-home"
            restore_backup(destination, restored_home, force=True, skip_secrets=True)

            self.assertFalse((restored_home / "auth.json").exists())
            self.assertFalse((restored_home / "cap_sid").exists())
            self.assertTrue((restored_home / "config.toml").exists())

    def test_verify_detects_tampered_backup(self) -> None:
        """Integrity verification should fail if a payload file is modified."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            codex_home = build_sample_codex_home(root)
            destination = root / "backup-dir"
            create_backup(codex_home, destination, force=True)

            tampered_file = destination / "payload" / "config.toml"
            tampered_file.write_text('model = "tampered"\n', encoding="utf-8")

            with self.assertRaises(BackupIntegrityError):
                verify_backup(destination)

    def test_restore_can_replace_destination_contents(self) -> None:
        """Replacing the destination should clear stale files before restore."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            codex_home = build_sample_codex_home(root)
            destination = root / "backup-dir"
            create_backup(codex_home, destination, force=True)

            restored_home = root / "restored-home"
            restored_home.mkdir(parents=True, exist_ok=True)
            (restored_home / "stale.txt").write_text("old", encoding="utf-8")
            (restored_home / "nested").mkdir(parents=True, exist_ok=True)
            (restored_home / "nested" / "stale.txt").write_text("old", encoding="utf-8")

            restore_backup(destination, restored_home, replace_destination=True)

            self.assertFalse((restored_home / "stale.txt").exists())
            self.assertFalse((restored_home / "nested").exists())
            self.assertTrue((restored_home / "config.toml").exists())


if __name__ == "__main__":
    unittest.main()
