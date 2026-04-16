from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


class ValidatorGatesBehaviorTests(unittest.TestCase):
    @property
    def _project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def _contracts_dir(self) -> Path:
        return self._project_root / "02_Contracts"

    @property
    def _automation_dir(self) -> Path:
        return self._project_root / "00_Project_Management" / "automation"

    def _copy_contracts(self, tmp_contracts_dir: Path, filenames: list[str]) -> None:
        tmp_contracts_dir.mkdir(parents=True, exist_ok=True)
        for name in filenames:
            shutil.copy2(self._contracts_dir / name, tmp_contracts_dir / name)

    def _run_validator(self, script_name: str, contracts_dir: Path, report_path: Path) -> subprocess.CompletedProcess[str]:
        script_path = self._automation_dir / script_name
        return subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--contracts-dir",
                str(contracts_dir),
                "--report-path",
                str(report_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_logsys_val_001_passes_on_valid_catalogs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            contracts_dir = tmp_dir / "contracts"
            report_path = tmp_dir / "report_001.json"
            self._copy_contracts(
                contracts_dir,
                [
                    "17_LoggingSystem_LogContainerProvider_Catalog_Contract.template.yaml",
                    "18_LoggingSystem_Connections_Catalog_Contract.template.yaml",
                    "19_LoggingSystem_Persistence_Catalog_Contract.template.yaml",
                ],
            )

            run = self._run_validator("validate_catalog_integrity_gate.py", contracts_dir, report_path)
            self.assertEqual(run.returncode, 0, msg=run.stdout + run.stderr)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["pass_fail"])
            self.assertEqual(payload["summary"]["violations_count"], 0)

    def test_logsys_val_001_fails_closed_on_broken_provider_connection_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            contracts_dir = tmp_dir / "contracts"
            report_path = tmp_dir / "report_001_fail.json"
            provider_file = contracts_dir / "17_LoggingSystem_LogContainerProvider_Catalog_Contract.template.yaml"
            self._copy_contracts(
                contracts_dir,
                [
                    "17_LoggingSystem_LogContainerProvider_Catalog_Contract.template.yaml",
                    "18_LoggingSystem_Connections_Catalog_Contract.template.yaml",
                    "19_LoggingSystem_Persistence_Catalog_Contract.template.yaml",
                ],
            )

            provider_payload = yaml.safe_load(provider_file.read_text(encoding="utf-8"))
            provider_payload["seed_entries"][0]["connection_profile_id"] = "connector.missing.invalid"
            provider_file.write_text(yaml.safe_dump(provider_payload, sort_keys=False), encoding="utf-8")

            run = self._run_validator("validate_catalog_integrity_gate.py", contracts_dir, report_path)
            self.assertNotEqual(run.returncode, 0, msg="validator must fail-closed")
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(payload["pass_fail"])
            codes = {item["code"] for item in payload["violations"]}
            self.assertIn("unresolved_provider_reference", codes)

    def test_logsys_val_002_passes_on_valid_threading_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            contracts_dir = tmp_dir / "contracts"
            report_path = tmp_dir / "report_002.json"
            self._copy_contracts(
                contracts_dir,
                [
                    "17_LoggingSystem_LogContainerProvider_Catalog_Contract.template.yaml",
                    "18_LoggingSystem_Connections_Catalog_Contract.template.yaml",
                    "19_LoggingSystem_Persistence_Catalog_Contract.template.yaml",
                    "22_LoggingSystem_ExecutionPool_Client_LeaseBinding_Contract.template.yaml",
                    "23_LoggingSystem_Threading_Scheduling_Backpressure_Contract.template.yaml",
                ],
            )

            run = self._run_validator("validate_threading_conformance_gate.py", contracts_dir, report_path)
            self.assertEqual(run.returncode, 0, msg=run.stdout + run.stderr)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["pass_fail"])
            self.assertEqual(payload["summary"]["violations_count"], 0)

    def test_logsys_val_002_fails_closed_on_non_orthogonal_execution_plane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            contracts_dir = tmp_dir / "contracts"
            report_path = tmp_dir / "report_002_fail.json"
            provider_file = contracts_dir / "17_LoggingSystem_LogContainerProvider_Catalog_Contract.template.yaml"
            self._copy_contracts(
                contracts_dir,
                [
                    "17_LoggingSystem_LogContainerProvider_Catalog_Contract.template.yaml",
                    "18_LoggingSystem_Connections_Catalog_Contract.template.yaml",
                    "19_LoggingSystem_Persistence_Catalog_Contract.template.yaml",
                    "22_LoggingSystem_ExecutionPool_Client_LeaseBinding_Contract.template.yaml",
                    "23_LoggingSystem_Threading_Scheduling_Backpressure_Contract.template.yaml",
                ],
            )

            provider_payload = yaml.safe_load(provider_file.read_text(encoding="utf-8"))
            provider_payload["seed_entries"][0]["execution_plane_relation"] = "merged_or_implicit"
            provider_file.write_text(yaml.safe_dump(provider_payload, sort_keys=False), encoding="utf-8")

            run = self._run_validator("validate_threading_conformance_gate.py", contracts_dir, report_path)
            self.assertNotEqual(run.returncode, 0, msg="validator must fail-closed")
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(payload["pass_fail"])
            codes = {item["code"] for item in payload["violations"]}
            self.assertIn("execution_plane_not_orthogonal", codes)


if __name__ == "__main__":
    unittest.main()
