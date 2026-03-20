"""Command-line interface for backup-codex."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import (
    BackupError,
    create_backup,
    human_bytes,
    inspect_codex_home,
    resolve_codex_home,
    restore_backup,
    verify_backup,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser and all supported subcommands."""

    parser = argparse.ArgumentParser(
        prog="codex-backup",
        description="Cria, verifica e restaura backups do diretório local do Codex.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspeciona o que entrará no backup.")
    inspect_parser.add_argument("--codex-home", help="Diretório base do Codex.")
    inspect_parser.add_argument("--mode", choices=("portable", "mirror"), default="portable")
    inspect_parser.add_argument(
        "--without-secrets",
        action="store_true",
        help="Exclui credenciais sensíveis do inventário.",
    )
    inspect_parser.add_argument("--json", action="store_true", help="Emite saída JSON.")

    backup_parser = subparsers.add_parser("backup", help="Cria um backup em diretório ou zip.")
    backup_parser.add_argument("destination", help="Diretório ou arquivo .zip de saída.")
    backup_parser.add_argument("--codex-home", help="Diretório base do Codex.")
    backup_parser.add_argument("--mode", choices=("portable", "mirror"), default="portable")
    backup_parser.add_argument(
        "--without-secrets",
        action="store_true",
        help="Não inclui credenciais sensíveis no backup.",
    )
    backup_parser.add_argument("--force", action="store_true", help="Sobrescreve o destino.")
    backup_parser.add_argument("--json", action="store_true", help="Emite saída JSON.")

    verify_parser = subparsers.add_parser("verify", help="Verifica a integridade de um backup.")
    verify_parser.add_argument("source", help="Diretório de backup ou arquivo .zip.")
    verify_parser.add_argument("--json", action="store_true", help="Emite saída JSON.")

    restore_parser = subparsers.add_parser("restore", help="Restaura um backup existente.")
    restore_parser.add_argument("source", help="Diretório de backup ou arquivo .zip.")
    restore_parser.add_argument(
        "target_codex_home",
        nargs="?",
        help="Diretório alvo do Codex. Padrão: diretório detectado localmente.",
    )
    restore_parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescreve arquivos existentes no destino.",
    )
    restore_parser.add_argument(
        "--skip-secrets",
        action="store_true",
        help="Não restaura credenciais sensíveis.",
    )
    restore_parser.add_argument(
        "--replace-destination",
        action="store_true",
        help="Limpa o conteúdo da pasta de destino antes de restaurar.",
    )
    restore_parser.add_argument("--json", action="store_true", help="Emite saída JSON.")

    return parser


def print_inspect(result: dict[str, object]) -> None:
    """Render a human-friendly summary for the ``inspect`` command."""

    summary = result["summary"]
    print(f"Codex home: {result['codex_home']}")
    print(f"Mode: {result['mode']}")
    print(f"Include secrets: {result['include_secrets']}")
    print(
        "Files: "
        f"{summary['files']} "
        f"({summary['regular_files']} regular, {summary['sqlite_databases']} sqlite, "
        f"{summary['secret_files']} secrets, {human_bytes(summary['total_bytes'])})"
    )
    preview = result["preview"]
    if preview:
        print("Preview:")
        for item in preview:
            print(f"  - {item}")


def print_manifest_result(
    *,
    action: str,
    path: Path,
    manifest_summary: dict[str, int],
    extra: str | None = None,
) -> None:
    """Render a human-friendly summary for backup, verify and restore."""

    print(f"{action}: {path}")
    print(
        "Summary: "
        f"{manifest_summary['files']} files, "
        f"{manifest_summary['sqlite_databases']} sqlite, "
        f"{manifest_summary['secret_files']} secrets, "
        f"{human_bytes(manifest_summary['total_bytes'])}"
    )
    if extra:
        print(extra)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "inspect":
            codex_home = resolve_codex_home(args.codex_home, must_exist=True)
            result = inspect_codex_home(
                codex_home,
                mode=args.mode,
                include_secrets=not args.without_secrets,
            )
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print_inspect(result)
            return 0

        if args.command == "backup":
            codex_home = resolve_codex_home(args.codex_home, must_exist=True)
            manifest = create_backup(
                codex_home,
                args.destination,
                mode=args.mode,
                include_secrets=not args.without_secrets,
                force=args.force,
            )
            result = {
                "destination": str(Path(args.destination).expanduser().resolve()),
                "codex_home": str(codex_home),
                "summary": manifest.summary,
                "mode": manifest.mode,
                "include_secrets": manifest.include_secrets,
            }
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print_manifest_result(
                    action="Backup created",
                    path=Path(result["destination"]),
                    manifest_summary=manifest.summary,
                    extra=f"Mode: {manifest.mode} | Include secrets: {manifest.include_secrets}",
                )
            return 0

        if args.command == "verify":
            manifest = verify_backup(args.source)
            result = {
                "source": str(Path(args.source).expanduser().resolve()),
                "summary": manifest.summary,
                "mode": manifest.mode,
                "include_secrets": manifest.include_secrets,
            }
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print_manifest_result(
                    action="Backup verified",
                    path=Path(result["source"]),
                    manifest_summary=manifest.summary,
                    extra="Integrity check passed.",
                )
            return 0

        if args.command == "restore":
            target_codex_home = resolve_codex_home(args.target_codex_home, must_exist=False)
            manifest = restore_backup(
                args.source,
                target_codex_home,
                force=args.force,
                skip_secrets=args.skip_secrets,
                replace_destination=args.replace_destination,
            )
            result = {
                "source": str(Path(args.source).expanduser().resolve()),
                "target_codex_home": str(target_codex_home),
                "summary": manifest.summary,
                "skip_secrets": args.skip_secrets,
                "replace_destination": args.replace_destination,
            }
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                notes: list[str] = []
                if args.skip_secrets:
                    notes.append("Secrets skipped during restore.")
                if args.replace_destination:
                    notes.append("Destination contents were replaced before restore.")
                print_manifest_result(
                    action="Backup restored",
                    path=target_codex_home,
                    manifest_summary=manifest.summary,
                    extra=" ".join(notes) if notes else None,
                )
            return 0
    except (BackupError, FileNotFoundError, FileExistsError, OSError) as exc:
        parser.exit(1, f"error: {exc}\n")

    parser.exit(1, "error: unsupported command\n")


if __name__ == "__main__":
    raise SystemExit(main())
