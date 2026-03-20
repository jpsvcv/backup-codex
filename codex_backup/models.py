"""Typed data models shared by backup creation, verification and restore."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

BackupMode = Literal["portable", "mirror"]
EntryKind = Literal["file", "sqlite"]


@dataclass(slots=True)
class BackupEntry:
    """Represents one file captured inside a backup payload."""

    relative_path: str
    kind: EntryKind
    size: int
    sha256: str = ""
    mtime: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupEntry":
        return cls(
            relative_path=str(data["relative_path"]),
            kind=data["kind"],
            size=int(data["size"]),
            sha256=str(data.get("sha256", "")),
            mtime=float(data.get("mtime", 0.0)),
        )


@dataclass(slots=True)
class BackupManifest:
    """Represents the metadata stored in ``manifest.json``."""

    schema_version: int
    tool_version: str
    created_at: str
    source_codex_home: str
    platform: str
    mode: BackupMode
    include_secrets: bool
    summary: dict[str, Any]
    entries: list[BackupEntry]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["entries"] = [entry.to_dict() for entry in self.entries]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupManifest":
        return cls(
            schema_version=int(data["schema_version"]),
            tool_version=str(data["tool_version"]),
            created_at=str(data["created_at"]),
            source_codex_home=str(data["source_codex_home"]),
            platform=str(data["platform"]),
            mode=data["mode"],
            include_secrets=bool(data["include_secrets"]),
            summary=dict(data["summary"]),
            entries=[BackupEntry.from_dict(item) for item in data["entries"]],
        )
