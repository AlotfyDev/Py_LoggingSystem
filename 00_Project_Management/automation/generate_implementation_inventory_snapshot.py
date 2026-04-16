from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SymbolEntry:
    rel_path: str
    constants: list[str]
    classes: list[str]
    functions: list[str]


def _collect_symbols(source_root: Path) -> list[SymbolEntry]:
    entries: list[SymbolEntry] = []
    for py_file in sorted(source_root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(source_root).as_posix()
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        constants: list[str] = []
        classes: list[str] = []
        functions: list[str] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants.append(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                constants.append(node.target.id)

        entries.append(
            SymbolEntry(
                rel_path=rel_path,
                constants=constants,
                classes=classes,
                functions=functions,
            )
        )
    return entries


def _group_key(rel_path: str) -> str:
    if rel_path.endswith("__init__.py"):
        return "Package Boundary / Module Exports"
    first = rel_path.split("/", 1)[0]
    if first == "models":
        return "Domain Models / Schema Catalog"
    if first == "ports":
        return "Port Contracts (Administrative / Managerial / Consuming / State)"
    if first == "adapters":
        return "Adapters / Factories (Provider Integrations + Persistence)"
    if first == "services":
        return "Service Orchestration / Runtime Logic"
    if first == "cli":
        return "CLI Control Plane"
    if first == "tests":
        return "Test Support + Behavioral/E2E Test Components"
    return "Other"


def _line_for(entry: SymbolEntry) -> str:
    tokens: list[str] = []
    if entry.constants:
        tokens.append("constants: " + ", ".join(f"`{name}`" for name in entry.constants))
    if entry.classes:
        tokens.append("classes: " + ", ".join(f"`{name}`" for name in entry.classes))
    if entry.functions:
        tokens.append("functions: " + ", ".join(f"`{name}`" for name in entry.functions))
    if not tokens:
        tokens.append("no top-level symbols")
    return f"`{entry.rel_path}`: " + "; ".join(tokens)


def _render_markdown(entries: list[SymbolEntry], source_root: Path, output_file: Path) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    sections_order = [
        "Package Boundary / Module Exports",
        "Domain Models / Schema Catalog",
        "Port Contracts (Administrative / Managerial / Consuming / State)",
        "Adapters / Factories (Provider Integrations + Persistence)",
        "Service Orchestration / Runtime Logic",
        "CLI Control Plane",
        "Test Support + Behavioral/E2E Test Components",
        "Other",
    ]
    grouped: dict[str, list[SymbolEntry]] = {name: [] for name in sections_order}
    for entry in entries:
        grouped.setdefault(_group_key(entry.rel_path), []).append(entry)

    lines: list[str] = []
    lines.append("# 02 LoggingSystem Implementation Inventory SSOT")
    lines.append("")
    lines.append("## Snapshot Metadata")
    lines.append(f"- generated_at_utc: `{generated_at}`")
    lines.append(f"- source_root: `{source_root.as_posix()}`")
    lines.append(f"- output_file: `{output_file.as_posix()}`")
    lines.append("- generated_by: `00_Project_Management/automation/generate_implementation_inventory_snapshot.py`")
    lines.append(f"- total_python_files_scanned: `{len(entries)}`")
    lines.append("")
    lines.append("## Regeneration Command")
    lines.append("```powershell")
    lines.append("python 03.0020_LoggingSystem/00_Project_Management/automation/generate_implementation_inventory_snapshot.py")
    lines.append("```")
    lines.append("")

    for section in sections_order:
        section_items = grouped.get(section, [])
        if len(section_items) == 0:
            continue
        lines.append(f"## {section}")
        for idx, entry in enumerate(section_items, start=1):
            lines.append(f"{idx}. {_line_for(entry)}")
        lines.append("")

    lines.append("## Maintenance Rule")
    lines.append("- Regenerate this snapshot whenever any file under `03_DigitalTwin/logging_system/` changes.")
    lines.append("- Treat this document as SSOT inventory evidence for implementation structure.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    script_path = Path(__file__).resolve()
    project_root = script_path.parents[2]
    source_root = project_root / "03_DigitalTwin" / "logging_system"
    output_file = project_root / "00_Project_Management" / "02_LoggingSystem_Implementation_Inventory_SSOT.md"

    entries = _collect_symbols(source_root)
    markdown = _render_markdown(entries, source_root, output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(markdown, encoding="utf-8")
    print(f"Generated: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
