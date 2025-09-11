#!/usr/bin/env python3
"""
Fail CI if we detect:
- stubs ('pass', '...') in function bodies
- NotImplementedError / TODO / FIXME
- wildcard imports, bare except
- sync 'requests.*' calls (use httpx)
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWLIST_DIRS = {
    "venv",
    ".venv",
    "site-packages",
    "__pycache__",
    "build",
    "dist",
    ".git",
}

PATTERNS = {
    r"^\s*pass\s*$": "Stub 'pass' found",
    r"^\s*\.\.\.\s*$": "Stub '...' found",
    r"NotImplementedError": "NotImplementedError left in code",
    r"#\s*(TODO|FIXME)\b": "TODO/FIXME comment left in code",
    r"from\s+[\w\.]+\s+import\s+\*": "Wildcard import",
    r"\bexcept\s*:\s*": "Bare except",
    (
        r"\brequests\.(get|post|put|delete|patch|head)\b"
    ): "Use httpx instead of requests",
}


def scan(path: pathlib.Path) -> list[str]:
    if any(part in ALLOWLIST_DIRS for part in path.parts):
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except (OSError, UnicodeError):  # pragma: no cover - file access issues
        return []
    findings: list[str] = []
    for i, line in enumerate(lines, 1):
        for pattern, message in PATTERNS.items():
            if re.search(pattern, line):
                findings.append(f"{path}:{i}: {message}: {line.strip()}")
    return findings


def main() -> int:
    findings: list[str] = []
    for file in ROOT.rglob("*.py"):
        findings.extend(scan(file))
    if findings:
        print("\n✖ repo_sanity found issues:\n" + "\n".join(findings))
        return 1
    print("✓ repo_sanity: clean")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
