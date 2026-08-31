"""Ensure Settings fields are documented in .env.example and secrets stay untracked."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "src" / "telco_digital" / "config" / "settings.py"
EXAMPLE = ROOT / ".env.example"
GITIGNORE = ROOT / ".gitignore"
ENV_ASSIGNMENT = re.compile(r"^[ \t]*#?[ \t]*([A-Z][A-Z0-9_]+)=", re.MULTILINE)
SECRET_NAME = re.compile(r"(^|/)\.env($|\.)")


def settings_env_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            return {
                item.target.id.upper()
                for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
    raise SystemExit("Settings class was not found")


def documented_env_names(path: Path) -> set[str]:
    return {match.group(1) for match in ENV_ASSIGNMENT.finditer(path.read_text(encoding="utf-8"))}


def gitignore_ignores_dotenv(path: Path) -> bool:
    lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    return ".env" in lines or ".env.*" in lines


def tracked_secret_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return []
    names = result.stdout.decode("utf-8").split("\0")
    return [
        name
        for name in names
        if name and SECRET_NAME.search(name) and not name.endswith(".env.example")
    ]


def main() -> int:
    errors: list[str] = []
    missing = sorted(settings_env_names(SETTINGS) - documented_env_names(EXAMPLE))
    if missing:
        errors.append("Settings fields missing from .env.example: " + ", ".join(missing))
    if not gitignore_ignores_dotenv(GITIGNORE):
        errors.append(".gitignore must ignore .env secret files")
    tracked = tracked_secret_files()
    if tracked:
        errors.append("Tracked secret env files: " + ", ".join(tracked))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
