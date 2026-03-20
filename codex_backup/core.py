"""Core backup, verification and restore primitives for backup-codex.

The module is intentionally self-contained so the CLI, tests and future
integrations can share the same trusted implementation.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from . import __version__
from .models import BackupEntry, BackupManifest, BackupMode

MANIFEST_NAME = "manifest.json"
PAYLOAD_DIR_NAME = "payload"
SECRET_FILES = {"auth.json", "cap_sid"}
PORTABLE_EXCLUDED_PREFIXES = (
    "tmp/",
    ".sandbox/",
    ".sandbox-bin/",
    ".sandbox-secrets/",
)
SQLITE_SIDE_SUFFIXES = (".sqlite-wal", ".sqlite-shm")


class BackupError(RuntimeError):
    """Raised when a backup or restore operation cannot be completed."""


class BackupIntegrityError(BackupError):
    """Raised when a backup does not match its manifest."""


def resolve_codex_home(
    explicit_path: str | os.PathLike[str] | None = None,
    *,
    must_exist: bool,
) -> Path:
    """Resolve the Codex home directory from an argument, env var or default."""

    if explicit_path:
        candidate = Path(explicit_path).expanduser()
    elif os.environ.get("CODEX_HOME"):
        candidate = Path(os.environ["CODEX_HOME"]).expanduser()
    else:
        candidate = Path.home() / ".codex"

    candidate = candidate.resolve()
    if must_exist and not candidate.exists():
        raise FileNotFoundError(f"Codex home not found: {candidate}")
    return candidate


def is_secret_path(relative_path: str) -> bool:
    """Return whether a relative backup path contains sensitive credentials."""

    return relative_path in SECRET_FILES


def is_excluded(relative_path: str, mode: BackupMode, include_secrets: bool) -> bool:
    """Return whether a path should be skipped for the selected backup mode."""

    if not include_secrets and is_secret_path(relative_path):
        return True
    if relative_path.endswith(SQLITE_SIDE_SUFFIXES):
        return True
    if mode == "portable":
        return any(relative_path.startswith(prefix) for prefix in PORTABLE_EXCLUDED_PREFIXES)
    return False


def collect_entries(
    codex_home: Path,
    *,
    mode: BackupMode = "portable",
    include_secrets: bool = True,
) -> list[BackupEntry]:
    """Walk the Codex directory and build the list of files to capture."""

    entries: list[BackupEntry] = []

    for current_root, dir_names, file_names in os.walk(codex_home):
        root_path = Path(current_root)
        relative_root = root_path.relative_to(codex_home).as_posix()
        if relative_root == ".":
            relative_root = ""
        relative_prefix = f"{relative_root}/" if relative_root else ""

        if mode == "portable":
            dir_names[:] = sorted(
                directory
                for directory in dir_names
                if not is_excluded(f"{relative_prefix}{directory}/", mode, True)
            )
        else:
            dir_names.sort()

        file_names.sort()
        for file_name in file_names:
            file_path = root_path / file_name
            relative_path = file_path.relative_to(codex_home).as_posix()
            if is_excluded(relative_path, mode, include_secrets):
                continue
            stat = file_path.stat()
            kind = "sqlite" if relative_path.endswith(".sqlite") else "file"
            entries.append(
                BackupEntry(
                    relative_path=relative_path,
                    kind=kind,
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                )
            )
    return entries


def build_summary(entries: list[BackupEntry]) -> dict[str, int]:
    """Aggregate a compact summary used by manifests and CLI output."""

    return {
        "files": len(entries),
        "regular_files": sum(entry.kind == "file" for entry in entries),
        "sqlite_databases": sum(entry.kind == "sqlite" for entry in entries),
        "secret_files": sum(is_secret_path(entry.relative_path) for entry in entries),
        "total_bytes": sum(entry.size for entry in entries),
    }


def human_bytes(value: int) -> str:
    """Convert a byte count to a short human-readable string."""

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def sha256_file(path: Path) -> str:
    """Compute the SHA-256 checksum of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_clean_destination(path: Path, *, force: bool) -> None:
    """Ensure a backup output path can be created without accidental overwrite."""

    if not path.exists():
        return
    if not force:
        raise FileExistsError(f"Destination already exists: {path}")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def write_json(path: Path, payload: dict) -> None:
    """Write a JSON file using UTF-8 and stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def snapshot_sqlite(source: Path, destination: Path) -> None:
    """Create a consistent SQLite snapshot using SQLite's native backup API."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_destination = destination.with_name(f"{destination.name}.tmp")
    if temporary_destination.exists():
        temporary_destination.unlink()

    source_connection = sqlite3.connect(str(source), timeout=30)
    target_connection = sqlite3.connect(str(temporary_destination))
    try:
        source_connection.execute("PRAGMA query_only = ON")
        source_connection.backup(target_connection)
    finally:
        target_connection.close()
        source_connection.close()

    temporary_destination.replace(destination)


def copy_regular_file(source: Path, destination: Path) -> None:
    """Copy a regular file while preserving metadata when possible."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def materialize_backup(
    codex_home: Path,
    backup_root: Path,
    *,
    mode: BackupMode,
    include_secrets: bool,
) -> BackupManifest:
    """Write the payload and manifest structure for a backup."""

    entries = collect_entries(codex_home, mode=mode, include_secrets=include_secrets)
    payload_root = backup_root / PAYLOAD_DIR_NAME
    payload_root.mkdir(parents=True, exist_ok=True)

    materialized_entries: list[BackupEntry] = []
    for entry in entries:
        source_path = codex_home / Path(entry.relative_path)
        destination_path = payload_root / Path(entry.relative_path)

        # SQLite files are snapshotted instead of copied raw so open databases
        # can be backed up consistently without depending on WAL sidecars.
        if entry.kind == "sqlite":
            snapshot_sqlite(source_path, destination_path)
        else:
            copy_regular_file(source_path, destination_path)

        stat = destination_path.stat()
        materialized_entries.append(
            BackupEntry(
                relative_path=entry.relative_path,
                kind=entry.kind,
                size=stat.st_size,
                sha256=sha256_file(destination_path),
                mtime=stat.st_mtime,
            )
        )

    manifest = BackupManifest(
        schema_version=1,
        tool_version=__version__,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_codex_home=str(codex_home),
        platform=platform.platform(),
        mode=mode,
        include_secrets=include_secrets,
        summary=build_summary(materialized_entries),
        entries=materialized_entries,
    )
    write_json(backup_root / MANIFEST_NAME, manifest.to_dict())
    return manifest


def create_backup(
    codex_home: Path,
    destination: str | os.PathLike[str],
    *,
    mode: BackupMode = "portable",
    include_secrets: bool = True,
    force: bool = False,
) -> BackupManifest:
    """Create a backup in either directory or ``.zip`` form."""

    destination_path = Path(destination).expanduser().resolve()
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    if destination_path.suffix.lower() == ".zip":
        return _create_zip_backup(
            codex_home,
            destination_path,
            mode=mode,
            include_secrets=include_secrets,
            force=force,
        )

    return _create_directory_backup(
        codex_home,
        destination_path,
        mode=mode,
        include_secrets=include_secrets,
        force=force,
    )


def _create_directory_backup(
    codex_home: Path,
    destination_path: Path,
    *,
    mode: BackupMode,
    include_secrets: bool,
    force: bool,
) -> BackupManifest:
    """Create a backup as a directory tree."""

    ensure_clean_destination(destination_path, force=force)
    temporary_root = Path(tempfile.mkdtemp(prefix="codex-backup-", dir=str(destination_path.parent)))
    try:
        manifest = materialize_backup(
            codex_home,
            temporary_root,
            mode=mode,
            include_secrets=include_secrets,
        )
        shutil.move(str(temporary_root), str(destination_path))
        return manifest
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root, ignore_errors=True)


def _create_zip_backup(
    codex_home: Path,
    destination_path: Path,
    *,
    mode: BackupMode,
    include_secrets: bool,
    force: bool,
) -> BackupManifest:
    """Create a backup as a compressed ``.zip`` archive."""

    ensure_clean_destination(destination_path, force=force)
    temporary_root = Path(tempfile.mkdtemp(prefix="codex-backup-", dir=str(destination_path.parent)))
    temporary_archive = destination_path.with_name(f"{destination_path.name}.tmp")
    if temporary_archive.exists():
        temporary_archive.unlink()

    try:
        manifest = materialize_backup(
            codex_home,
            temporary_root,
            mode=mode,
            include_secrets=include_secrets,
        )
        with zipfile.ZipFile(temporary_archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(temporary_root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(temporary_root).as_posix())
        temporary_archive.replace(destination_path)
        return manifest
    finally:
        if temporary_archive.exists():
            temporary_archive.unlink(missing_ok=True)
        if temporary_root.exists():
            shutil.rmtree(temporary_root, ignore_errors=True)


def load_manifest(backup_root: Path) -> BackupManifest:
    """Load and deserialize ``manifest.json`` from a backup root."""

    manifest_path = backup_root / MANIFEST_NAME
    if not manifest_path.exists():
        raise BackupError(f"Manifest not found in backup: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return BackupManifest.from_dict(payload)


def verify_manifest_summary(manifest: BackupManifest) -> None:
    """Ensure the manifest summary still matches the entry list."""

    expected_files = manifest.summary.get("files")
    expected_bytes = manifest.summary.get("total_bytes")
    actual_files = len(manifest.entries)
    actual_bytes = sum(entry.size for entry in manifest.entries)

    if expected_files != actual_files:
        raise BackupIntegrityError(
            f"Manifest summary mismatch: expected {expected_files} files, found {actual_files}"
        )
    if expected_bytes != actual_bytes:
        raise BackupIntegrityError(
            f"Manifest summary mismatch: expected {expected_bytes} bytes, found {actual_bytes}"
        )


@contextmanager
def open_backup_root(source: str | os.PathLike[str]) -> Iterator[Path]:
    """Yield a backup root from either a directory backup or a zip backup."""

    source_path = Path(source).expanduser().resolve()
    if source_path.is_dir():
        yield source_path
        return

    if source_path.suffix.lower() != ".zip":
        raise BackupError(f"Unsupported backup format: {source_path}")

    with tempfile.TemporaryDirectory(prefix="codex-backup-restore-") as temp_dir:
        temporary_root = Path(temp_dir)
        with zipfile.ZipFile(source_path, "r") as archive:
            archive.extractall(temporary_root)
        yield temporary_root


def cleanup_sqlite_sidecars(database_path: Path) -> None:
    """Remove SQLite sidecars that could conflict with a restored database."""

    for suffix in ("-wal", "-shm"):
        database_path.with_name(f"{database_path.name}{suffix}").unlink(missing_ok=True)


def verify_backup_root(backup_root: Path) -> BackupManifest:
    """Verify the payload inside an already-opened backup root."""

    manifest = load_manifest(backup_root)
    verify_manifest_summary(manifest)

    payload_root = backup_root / PAYLOAD_DIR_NAME
    if not payload_root.exists():
        raise BackupIntegrityError(f"Payload directory not found in backup: {payload_root}")

    for entry in manifest.entries:
        source_path = payload_root / Path(entry.relative_path)
        if not source_path.exists():
            raise BackupIntegrityError(f"Backup payload is missing: {source_path}")
        if source_path.is_dir():
            raise BackupIntegrityError(f"Backup payload should be a file, but is a directory: {source_path}")

        stat = source_path.stat()
        if stat.st_size != entry.size:
            raise BackupIntegrityError(
                f"Size mismatch for {entry.relative_path}: expected {entry.size}, got {stat.st_size}"
            )
        if not entry.sha256:
            raise BackupIntegrityError(f"Manifest is missing SHA-256 for {entry.relative_path}")

        actual_hash = sha256_file(source_path)
        if actual_hash != entry.sha256:
            raise BackupIntegrityError(
                f"SHA-256 mismatch for {entry.relative_path}: expected {entry.sha256}, got {actual_hash}"
            )

    return manifest


def verify_backup(source: str | os.PathLike[str]) -> BackupManifest:
    """Verify a backup directory or zip file against its manifest."""

    with open_backup_root(source) as backup_root:
        return verify_backup_root(backup_root)


def validate_replace_destination(target_codex_home: Path) -> None:
    """Refuse destructive replace operations on clearly dangerous paths."""

    resolved_target = target_codex_home.resolve()
    dangerous_paths = {
        Path(resolved_target.anchor),
        Path.home().resolve(),
        Path.home().resolve().parent,
    }
    if resolved_target in dangerous_paths:
        raise BackupError(
            f"Refusing to replace the contents of a dangerous destination path: {resolved_target}"
        )


def clear_directory_contents(target_codex_home: Path) -> None:
    """Delete the contents of the restore destination without deleting the root."""

    if not target_codex_home.exists():
        return
    if not target_codex_home.is_dir():
        raise BackupError(f"Restore target is not a directory: {target_codex_home}")

    validate_replace_destination(target_codex_home)
    for child in target_codex_home.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def restore_backup(
    source: str | os.PathLike[str],
    target_codex_home: Path,
    *,
    force: bool = False,
    skip_secrets: bool = False,
    replace_destination: bool = False,
) -> BackupManifest:
    """Restore a backup after verifying its integrity."""

    with open_backup_root(source) as backup_root:
        # The restore process refuses to touch the destination until the backup
        # passes integrity validation. This avoids replacing good data with a
        # corrupted or incomplete package.
        manifest = verify_backup_root(backup_root)
        payload_root = backup_root / PAYLOAD_DIR_NAME

        if target_codex_home.exists() and not target_codex_home.is_dir():
            raise BackupError(f"Restore target is not a directory: {target_codex_home}")
        target_codex_home.mkdir(parents=True, exist_ok=True)

        if replace_destination:
            # This mode intentionally replaces the destination contents, which is
            # useful for disaster recovery or migration to another computer.
            clear_directory_contents(target_codex_home)
        else:
            collisions: list[str] = []
            for entry in manifest.entries:
                if skip_secrets and is_secret_path(entry.relative_path):
                    continue
                destination_path = target_codex_home / Path(entry.relative_path)
                if destination_path.exists() and not force:
                    collisions.append(entry.relative_path)

            if collisions:
                preview = ", ".join(collisions[:5])
                raise FileExistsError(
                    f"Restore would overwrite existing files. Re-run with --force. Examples: {preview}"
                )

        for entry in manifest.entries:
            if skip_secrets and is_secret_path(entry.relative_path):
                continue

            source_path = payload_root / Path(entry.relative_path)
            if not source_path.exists():
                raise BackupError(f"Backup payload is missing: {source_path}")

            destination_path = target_codex_home / Path(entry.relative_path)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if destination_path.exists() and force:
                if destination_path.is_dir():
                    shutil.rmtree(destination_path)
                else:
                    destination_path.unlink()
            shutil.copy2(source_path, destination_path)
            if entry.kind == "sqlite":
                cleanup_sqlite_sidecars(destination_path)

        return manifest


def inspect_codex_home(
    codex_home: Path,
    *,
    mode: BackupMode = "portable",
    include_secrets: bool = True,
) -> dict[str, object]:
    """Build a lightweight report showing what a backup would include."""

    entries = collect_entries(codex_home, mode=mode, include_secrets=include_secrets)
    summary = build_summary(entries)
    return {
        "codex_home": str(codex_home),
        "mode": mode,
        "include_secrets": include_secrets,
        "summary": summary,
        "preview": [entry.relative_path for entry in entries[:10]],
    }
