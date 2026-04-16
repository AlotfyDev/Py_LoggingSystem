from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    context: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_yaml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - fail-closed diagnostics
        return None, f"yaml_parse_failure: {path.name}: {exc}"
    if not isinstance(payload, dict):
        return None, f"yaml_parse_failure: {path.name}: root_not_mapping"
    return payload, None


def _entry_id_map(entries: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for entry in entries:
        entry_id = entry.get(key)
        if isinstance(entry_id, str) and entry_id.strip() != "":
            mapping[entry_id] = entry
    return mapping


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _ack_compatible(provider_ack: str, persistence_ack: str) -> bool:
    return provider_ack.strip() == persistence_ack.strip()


def _build_parser(default_contracts_dir: Path, default_report_path: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LOGSYS-VAL-001 catalog integrity validator")
    parser.add_argument(
        "--contracts-dir",
        default=str(default_contracts_dir),
        help="Path to contracts directory containing 17/18/19 catalog contracts.",
    )
    parser.add_argument(
        "--report-path",
        default=str(default_report_path),
        help="Path to write validator JSON report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    script_path = Path(__file__).resolve()
    project_root = script_path.parents[2]
    default_contracts_dir = project_root / "02_Contracts"
    default_report_path = project_root / "00_Project_Management" / "05_LOGSYS_VAL_Catalog_Integrity_Report.json"

    parser = _build_parser(default_contracts_dir, default_report_path)
    args = parser.parse_args(argv)
    contracts_dir = Path(args.contracts_dir).resolve()
    report_path = Path(args.report_path).resolve()

    contract_paths = {
        "provider": contracts_dir / "17_LoggingSystem_LogContainerProvider_Catalog_Contract.template.yaml",
        "connection": contracts_dir / "18_LoggingSystem_Connections_Catalog_Contract.template.yaml",
        "persistence": contracts_dir / "19_LoggingSystem_Persistence_Catalog_Contract.template.yaml",
    }

    violations: list[Violation] = []
    contract_payloads: dict[str, dict[str, Any]] = {}

    for contract_name, contract_path in contract_paths.items():
        if not contract_path.exists():
            violations.append(
                Violation(
                    code="missing_catalog_contract_file",
                    message="Required catalog contract is missing.",
                    context={"contract": contract_name, "path": str(contract_path)},
                )
            )
            continue
        payload, load_error = _load_yaml(contract_path)
        if load_error is not None:
            violations.append(
                Violation(
                    code="yaml_parse_failure",
                    message=load_error,
                    context={"contract": contract_name, "path": str(contract_path)},
                )
            )
            continue
        contract_payloads[contract_name] = payload

    provider_contract = contract_payloads.get("provider", {})
    connection_contract = contract_payloads.get("connection", {})
    persistence_contract = contract_payloads.get("persistence", {})

    provider_catalog = provider_contract.get("catalog_model", {})
    connection_catalog = connection_contract.get("catalog_model", {})
    persistence_catalog = persistence_contract.get("catalog_model", {})

    provider_entries = _as_list(provider_contract.get("seed_entries"))
    connection_entries = _as_list(connection_contract.get("seed_entries"))
    persistence_entries = _as_list(persistence_contract.get("seed_entries"))

    required_provider_fields = _as_list(provider_catalog.get("required_fields"))
    allowed_backend_types = set(_as_list(provider_catalog.get("allowed_backend_types")))
    allowed_scope_support = set(_as_list(provider_catalog.get("allowed_scope_support")))
    allowed_partition_modes = set(_as_list(provider_catalog.get("allowed_partition_modes")))

    connection_by_id = _entry_id_map(connection_entries, "connector_profile_id")
    persistence_by_id = _entry_id_map(persistence_entries, "persistence_profile_id")

    for provider_entry in provider_entries:
        provider_id = provider_entry.get("provider_id")
        if not isinstance(provider_id, str) or provider_id.strip() == "":
            violations.append(
                Violation(
                    code="provider_missing_required_field",
                    message="Provider entry is missing required field provider_id.",
                    context={"entry": provider_entry},
                )
            )
            continue

        for field_name in required_provider_fields:
            if field_name not in provider_entry:
                violations.append(
                    Violation(
                        code="provider_missing_required_field",
                        message="Provider entry is missing required field.",
                        context={"provider_id": provider_id, "missing_field": field_name},
                    )
                )

        backend_type = provider_entry.get("backend_type")
        if isinstance(backend_type, str) and allowed_backend_types and backend_type not in allowed_backend_types:
            violations.append(
                Violation(
                    code="provider_entry_with_unsupported_backend_type",
                    message="Provider backend_type is not allowed by catalog.",
                    context={"provider_id": provider_id, "backend_type": backend_type},
                )
            )

        for scope_value in _as_list(provider_entry.get("scope_support")):
            if isinstance(scope_value, str) and allowed_scope_support and scope_value not in allowed_scope_support:
                violations.append(
                    Violation(
                        code="provider_scope_support_outside_allowed_values",
                        message="Provider scope_support contains unsupported value.",
                        context={"provider_id": provider_id, "scope_support": scope_value},
                    )
                )

        for partition_mode in _as_list(provider_entry.get("supported_partition_modes")):
            if isinstance(partition_mode, str) and allowed_partition_modes and partition_mode not in allowed_partition_modes:
                violations.append(
                    Violation(
                        code="provider_partition_mode_outside_allowed_values",
                        message="Provider supported_partition_modes contains unsupported value.",
                        context={"provider_id": provider_id, "partition_mode": partition_mode},
                    )
                )

        connection_profile_id = provider_entry.get("connection_profile_id")
        persistence_profile_id = provider_entry.get("persistence_profile_id")
        provider_ack_model = str(provider_entry.get("ack_model", ""))

        connection_entry = (
            connection_by_id.get(connection_profile_id) if isinstance(connection_profile_id, str) else None
        )
        persistence_entry = (
            persistence_by_id.get(persistence_profile_id) if isinstance(persistence_profile_id, str) else None
        )

        if connection_entry is None:
            violations.append(
                Violation(
                    code="unresolved_provider_reference",
                    message="Provider connection_profile_id reference does not resolve.",
                    context={
                        "provider_id": provider_id,
                        "connection_profile_id": connection_profile_id,
                    },
                )
            )
        else:
            connection_provider_id = connection_entry.get("provider_id")
            if connection_provider_id != provider_id:
                violations.append(
                    Violation(
                        code="provider_connection_provider_id_mismatch",
                        message="Connection provider_id does not match provider entry provider_id.",
                        context={
                            "provider_id": provider_id,
                            "connection_profile_id": connection_profile_id,
                            "connection_provider_id": connection_provider_id,
                        },
                    )
                )

        if persistence_entry is None:
            violations.append(
                Violation(
                    code="unresolved_provider_reference",
                    message="Provider persistence_profile_id reference does not resolve.",
                    context={
                        "provider_id": provider_id,
                        "persistence_profile_id": persistence_profile_id,
                    },
                )
            )
        else:
            persistence_provider_id = persistence_entry.get("provider_id")
            if persistence_provider_id != provider_id:
                violations.append(
                    Violation(
                        code="provider_persistence_provider_id_mismatch",
                        message="Persistence provider_id does not match provider entry provider_id.",
                        context={
                            "provider_id": provider_id,
                            "persistence_profile_id": persistence_profile_id,
                            "persistence_provider_id": persistence_provider_id,
                        },
                    )
                )

            persistence_ack = str(persistence_entry.get("ack_semantics", ""))
            if not _ack_compatible(provider_ack_model, persistence_ack):
                violations.append(
                    Violation(
                        code="ack_semantics_incompatibility",
                        message="Provider ack_model is incompatible with persistence ack_semantics.",
                        context={
                            "provider_id": provider_id,
                            "provider_ack_model": provider_ack_model,
                            "persistence_ack_semantics": persistence_ack,
                            "persistence_profile_id": persistence_profile_id,
                        },
                    )
                )

    report_payload = {
        "gate_id": "LOGSYS-VAL-001",
        "generated_at_utc": _utc_now(),
        "pass_fail": len(violations) == 0,
        "summary": {
            "provider_entries_scanned": len(provider_entries),
            "connection_entries_scanned": len(connection_entries),
            "persistence_entries_scanned": len(persistence_entries),
            "violations_count": len(violations),
        },
        "violations": [
            {"code": item.code, "message": item.message, "context": item.context}
            for item in violations
        ],
        "sources": {
            "provider_contract": str(contract_paths["provider"]),
            "connection_contract": str(contract_paths["connection"]),
            "persistence_contract": str(contract_paths["persistence"]),
        },
        "catalog_model_ids": {
            "provider": provider_catalog.get("catalog_id"),
            "connection": connection_catalog.get("catalog_id"),
            "persistence": persistence_catalog.get("catalog_id"),
        },
    }

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    except Exception as exc:  # pragma: no cover - fail-closed diagnostics
        print(f"ERROR: report_write_failure: {exc}")
        return 1

    if report_payload["pass_fail"]:
        print("LOGSYS-VAL-001: PASS")
        return 0

    print("LOGSYS-VAL-001: FAIL")
    for item in violations:
        print(f"[{item.code}] {item.message} :: {item.context}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
