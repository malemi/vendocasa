#!/usr/bin/env python3
"""Search kept evidence for a VendoCasa project's secret values.

    deploy/scan_evidence.py <vendocasa|vendocasa-rehearsal> <path> [<path>...]

The values are the project's generated database passwords, signing secret
and service key (~/.config/vendocasa/<project>/generated.env) and, for
production, the operator's provider key, SMTP password and source database
URL with its password (~/.config/vendocasa/secrets.env). The public client
key is public and is not searched. Every file under the given paths is read
as bytes. The scan prints only file names and match counts, never a value,
and exits with 1 when it finds any. Python standard library only.
"""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

CONFIG = Path.home() / ".config" / "vendocasa"
MIN_LENGTH = 12  # shorter values are placeholders, not secrets


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep:
                values[key.strip()] = value.strip()
    return values


def secret_values(project: str) -> dict[str, bytes]:
    generated = read_env(CONFIG / project / "generated.env")
    found = {name: generated.get(name, "") for name in
             ("POSTGRES_PASSWORD", "AUTH_DB_PASSWORD", "JWT_SECRET", "SERVICE_ROLE_KEY")}
    if project == "vendocasa":
        operator = read_env(CONFIG / "secrets.env")
        for name in ("ANTHROPIC_API_KEY", "SMTP_PASS", "SUPABASE_SOURCE_DATABASE_URL"):
            found[name] = operator.get(name, "")
        password = urllib.parse.urlsplit(found["SUPABASE_SOURCE_DATABASE_URL"]).password or ""
        found["source database password"] = urllib.parse.unquote(password)
    missing = [name for name in ("POSTGRES_PASSWORD", "JWT_SECRET") if not found[name]]
    if missing:
        raise SystemExit(f"scan_evidence.py: {', '.join(missing)} not found for {project}")
    return {name: value.encode() for name, value in found.items() if len(value) >= MIN_LENGTH}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    values = secret_values(argv[0])
    files = 0
    hits = 0
    for root in map(Path, argv[1:]):
        for path in [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file()):
            files += 1
            data = path.read_bytes()
            for name, value in values.items():
                count = data.count(value)
                if count:
                    hits += count
                    print(f"FOUND {name} x{count} in {path}")
    print(f"scan_evidence.py: {len(values)} secret values searched in {files} files; {hits} matches")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
