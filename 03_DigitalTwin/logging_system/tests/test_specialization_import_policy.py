from __future__ import annotations

from pathlib import Path
import unittest


class SpecializationImportPolicyTests(unittest.TestCase):
    def test_forbidden_ovs_internal_import_roots_not_used(self) -> None:
        root = Path(__file__).resolve().parents[1]
        forbidden = [
            "observability_viewer_system.viewer_core",
            "observability_viewer_system.format_registry",
            "observability_viewer_system.adapters",
            "observability_viewer_system.render_ports",
            "observability_viewer_system.services",
        ]
        allowed_wrapper = root / "specialization" / "logging_viewer_specialization.py"

        for py_file in root.rglob("*.py"):
            if "tests" in py_file.parts:
                continue
            text = py_file.read_text(encoding="utf-8")
            for forbidden_root in forbidden:
                if forbidden_root in text:
                    self.fail(f"Forbidden OVS internal import root found in {py_file}: {forbidden_root}")

            if py_file != allowed_wrapper and "observability_viewer_system.specialized" in text:
                self.fail(
                    f"Only specialization wrapper may import OVS specialized API directly: {py_file}"
                )


if __name__ == "__main__":
    unittest.main()
