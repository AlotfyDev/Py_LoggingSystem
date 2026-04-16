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


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _profile_map(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for entry in entries:
        profile_id = entry.get("execution_profile_id")
        if isinstance(profile_id, str) and profile_id.strip() != "":
            mapping[profile_id] = entry
    return mapping


def _build_parser(default_contracts_dir: Path, default_report_path: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LOGSYS-VAL-002 threading conformance validator")
    parser.add_argument(
        "--contracts-dir",
        default=str(default_contracts_dir),
        help="Path to contracts directory containing 17/18/19/22/23 contracts.",
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
    default_report_path = project_root / "00_Project_Management" / "06_LOGSYS_VAL_Threading_Conformance_Report.json"

    parser = _build_parser(default_contracts_dir, default_report_path)
    args = parser.parse_args(argv)
    contracts_dir = Path(args.contracts_dir).resolve()
    report_path = Path(args.report_path).resolve()

    contract_paths = {
        "provider": contracts_dir / "17_LoggingSystem_LogContainerProvider_Catalog_Contract.template.yaml",
        "connection": contracts_dir / "18_LoggingSystem_Connections_Catalog_Contract.template.yaml",
        "persistence": contracts_dir / "19_LoggingSystem_Persistence_Catalog_Contract.template.yaml",
        "execution": contracts_dir / "22_LoggingSystem_ExecutionPool_Client_LeaseBinding_Contract.template.yaml",
        "threading": contracts_dir / "23_LoggingSystem_Threading_Scheduling_Backpressure_Contract.template.yaml",
    }

    violations: list[Violation] = []
    payloads: dict[str, dict[str, Any]] = {}

    for name, path in contract_paths.items():
        if not path.exists():
            violations.append(
                Violation(
                    code="missing_catalog_contract_file",
                    message="Required contract file is missing.",
                    context={"contract": name, "path": str(path)},
                )
            )
            continue
        payload, err = _load_yaml(path)
        if err is not None:
            violations.append(
                Violation(
                    code="yaml_parse_failure",
                    message=err,
                    context={"contract": name, "path": str(path)},
                )
            )
            continue
        payloads[name] = payload

    provider_entries = _as_list(payloads.get("provider", {}).get("seed_entries"))
    connection_entries = _as_list(payloads.get("connection", {}).get("seed_entries"))
    persistence_entries = _as_list(payloads.get("persistence", {}).get("seed_entries"))
    execution_entries = _as_list(
        payloads.get("execution", {}).get("execution_profile_catalog", {}).get("seed_entries")
    )
    threading_model = payloads.get("threading", {}).get("threading_model", {})

    profile_by_id = _profile_map(execution_entries)
    allowed_thread_safety_modes = set(_as_list(threading_model.get("allowed_thread_safety_modes")))
    allowed_queue_models = set(_as_list(threading_model.get("allowed_queue_models")))
    allowed_backpressure_actions = set(_as_list(threading_model.get("allowed_backpressure_actions")))

    for provider in provider_entries:
        provider_id = provider.get("provider_id")
        if not isinstance(provider_id, str) or provider_id.strip() == "":
            violations.append(
                Violation(
                    code="provider_missing_required_field",
                    message="Provider entry missing provider_id.",
                    context={"provider_entry": provider},
                )
            )
            continue

        if provider.get("execution_plane_relation") != "orthogonal_explicit_binding":
            violations.append(
                Violation(
                    code="execution_plane_not_orthogonal",
                    message="Provider execution plane relation must be orthogonal_explicit_binding.",
                    context={
                        "provider_id": provider_id,
                        "execution_plane_relation": provider.get("execution_plane_relation"),
                    },
                )
            )

        profile_id = provider.get("required_execution_profile_id")
        if not isinstance(profile_id, str) or profile_id.strip() == "":
            violations.append(
                Violation(
                    code="provider_missing_execution_profile_reference",
                    message="Provider missing required_execution_profile_id.",
                    context={"provider_id": provider_id},
                )
            )
            continue

        profile = profile_by_id.get(profile_id)
        if profile is None:
            violations.append(
                Violation(
                    code="provider_execution_profile_reference_unresolved",
                    message="Provider required_execution_profile_id does not resolve.",
                    context={"provider_id": provider_id, "required_execution_profile_id": profile_id},
                )
            )
            continue

        queue_model = profile.get("queue_model")
        if queue_model not in allowed_queue_models:
            violations.append(
                Violation(
                    code="execution_profile_queue_model_not_allowed",
                    message="Execution profile queue_model is not allowed.",
                    context={
                        "provider_id": provider_id,
                        "execution_profile_id": profile_id,
                        "queue_model": queue_model,
                    },
                )
            )

        queue_bounds = profile.get("queue_bounds")
        max_items = queue_bounds.get("max_items") if isinstance(queue_bounds, dict) else None
        if not isinstance(max_items, int) or max_items <= 0:
            violations.append(
                Violation(
                    code="unbounded_or_invalid_queue_bounds",
                    message="Execution profile queue_bounds.max_items must be a positive integer.",
                    context={
                        "provider_id": provider_id,
                        "execution_profile_id": profile_id,
                        "queue_bounds": queue_bounds,
                    },
                )
            )

        thread_safety_mode = profile.get("thread_safety_mode")
        if thread_safety_mode not in allowed_thread_safety_modes:
            violations.append(
                Violation(
                    code="execution_profile_thread_safety_mode_not_allowed",
                    message="Execution profile thread_safety_mode is not allowed.",
                    context={
                        "provider_id": provider_id,
                        "execution_profile_id": profile_id,
                        "thread_safety_mode": thread_safety_mode,
                    },
                )
            )

        backpressure_policy = profile.get("backpressure_policy")
        action = backpressure_policy.get("action") if isinstance(backpressure_policy, dict) else None
        if action not in allowed_backpressure_actions:
            violations.append(
                Violation(
                    code="unsupported_backpressure_action",
                    message="Execution profile backpressure action is not allowed.",
                    context={
                        "provider_id": provider_id,
                        "execution_profile_id": profile_id,
                        "backpressure_action": action,
                    },
                )
            )

        if isinstance(backpressure_policy, dict):
            overrides = backpressure_policy.get("severity_overrides")
            if isinstance(overrides, dict):
                for severity_key, severity_action in overrides.items():
                    if severity_action not in allowed_backpressure_actions:
                        violations.append(
                            Violation(
                                code="unsupported_backpressure_action",
                                message="Backpressure severity override action is not allowed.",
                                context={
                                    "provider_id": provider_id,
                                    "execution_profile_id": profile_id,
                                    "severity": severity_key,
                                    "action": severity_action,
                                },
                            )
                        )

        provider_lease_required = bool(provider.get("lease_required", False))
        lease_policy = profile.get("lease_policy")
        profile_lease_required = (
            bool(lease_policy.get("required", False)) if isinstance(lease_policy, dict) else False
        )
        if provider_lease_required and not profile_lease_required:
            violations.append(
                Violation(
                    code="lease_required_mismatch",
                    message="Provider requires lease but execution profile lease_policy.required is false.",
                    context={
                        "provider_id": provider_id,
                        "execution_profile_id": profile_id,
                    },
                )
            )

    for connection in connection_entries:
        if connection.get("execution_plane_relation") != "orthogonal_explicit_binding":
            violations.append(
                Violation(
                    code="execution_plane_not_orthogonal",
                    message="Connection execution plane relation must be orthogonal_explicit_binding.",
                    context={"connector_profile_id": connection.get("connector_profile_id")},
                )
            )

    for persistence in persistence_entries:
        if persistence.get("execution_plane_relation") != "orthogonal_explicit_binding":
            violations.append(
                Violation(
                    code="execution_plane_not_orthogonal",
                    message="Persistence execution plane relation must be orthogonal_explicit_binding.",
                    context={"persistence_profile_id": persistence.get("persistence_profile_id")},
                )
            )

    report_payload = {
        "gate_id": "LOGSYS-VAL-002",
        "generated_at_utc": _utc_now(),
        "pass_fail": len(violations) == 0,
        "summary": {
            "provider_entries_scanned": len(provider_entries),
            "execution_profiles_scanned": len(execution_entries),
            "connection_entries_scanned": len(connection_entries),
            "persistence_entries_scanned": len(persistence_entries),
            "violations_count": len(violations),
        },
        "violations": [
            {"code": violation.code, "message": violation.message, "context": violation.context}
            for violation in violations
        ],
        "sources": {name: str(path) for name, path in contract_paths.items()},
    }

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    except Exception as exc:  # pragma: no cover - fail-closed diagnostics
        print(f"ERROR: report_write_failure: {exc}")
        return 1

    if report_payload["pass_fail"]:
        print("LOGSYS-VAL-002: PASS")
        return 0

    print("LOGSYS-VAL-002: FAIL")
    for violation in violations:
        print(f"[{violation.code}] {violation.message} :: {violation.context}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
