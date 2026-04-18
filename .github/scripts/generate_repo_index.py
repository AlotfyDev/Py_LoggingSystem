from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(".").resolve()
OUTPUT = ROOT / "repo-index.json"

REPO = os.environ.get("GITHUB_REPOSITORY", "")
BRANCH = os.environ.get("GITHUB_REF_NAME", "")

EXCLUDED_FILES = {
    "repo-index.json",
}
EXCLUDED_DIRS = {
    ".git",
}


def iter_repo_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue

        rel = path.relative_to(root)

        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue

        if rel.name in EXCLUDED_FILES:
            continue

        yield rel


def classify_file(rel: Path) -> str:
    parts = [p.lower() for p in rel.parts]
    name = rel.name.lower()
    suffix = rel.suffix.lower()

    if parts and parts[0] == ".github":
        if len(parts) > 1 and parts[1] == "workflows":
            return "workflow"
        return "repo_meta"

    if parts and parts[0] == "tests":
        return "test"

    if parts and parts[0] in {"docs", "doc", "documentation"}:
        return "documentation"

    if suffix in {".md", ".rst", ".txt"}:
        return "documentation"

    if suffix in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}:
        return "config"

    if suffix in {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"}:
        return "asset"

    if suffix in {".csv", ".tsv", ".parquet", ".h5", ".hdf5"}:
        return "data"

    if suffix in {".py", ".js", ".ts", ".java", ".go", ".c", ".cpp", ".rb", ".php", ".sh", ".ps1"}:
        return "code"

    return "unknown"


def build_raw_url(rel: Path) -> str:
    encoded = quote(rel.as_posix(), safe="/")
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{encoded}"


def build_github_url(rel: Path) -> str:
    encoded = quote(rel.as_posix(), safe="/")
    return f"https://github.com/{REPO}/blob/{BRANCH}/{encoded}"


def is_hidden(rel: Path) -> bool:
    return any(part.startswith(".") for part in rel.parts)


def is_test(rel: Path) -> bool:
    parts = [p.lower() for p in rel.parts]
    name = rel.name.lower()
    return (
        "tests" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or "test" in name
    )


def is_workflow(rel: Path) -> bool:
    parts = [p.lower() for p in rel.parts]
    return len(parts) >= 2 and parts[0] == ".github" and parts[1] == "workflows"


def is_doc(rel: Path) -> bool:
    parts = [p.lower() for p in rel.parts]
    suffix = rel.suffix.lower()
    return (
        (parts and parts[0] in {"docs", "doc", "documentation"})
        or suffix in {".md", ".rst", ".txt"}
    )


def main() -> None:
    files = []
    top_level_dirs = set()

    for rel in sorted(iter_repo_files(ROOT), key=lambda p: p.as_posix().lower()):
        full = ROOT / rel
        stat = full.stat()

        top_level = rel.parts[0] if rel.parts else ""
        if top_level:
            top_level_dirs.add(top_level)

        files.append(
            {
                "path": rel.as_posix(),
                "filename": rel.name,
                "stem": rel.stem,
                "extension": rel.suffix.lower().lstrip("."),
                "size_bytes": stat.st_size,
                "top_level_dir": top_level,
                "path_depth": len(rel.parts),
                "category": classify_file(rel),
                "is_hidden": is_hidden(rel),
                "is_test": is_test(rel),
                "is_workflow": is_workflow(rel),
                "is_doc": is_doc(rel),
                "raw_url": build_raw_url(rel),
                "github_url": build_github_url(rel),
            }
        )

    payload = {
        "schema_version": "repo-index.v2",
        "generated_by": "create-repo-index.yml",
        "repo": REPO,
        "branch": BRANCH,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "file_count": len(files),
        "top_level_dirs": sorted(top_level_dirs, key=str.lower),
        "files": files,
    }

    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
