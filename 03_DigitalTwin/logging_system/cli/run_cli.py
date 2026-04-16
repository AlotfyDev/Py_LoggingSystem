from __future__ import annotations

import json
import sys

from ..adapters.default_state_store_factory import build_default_state_store
from ..services.logging_service import LoggingService
from .json_payload_parser import parse_json_object
from .parser import build_parser


def run_cli(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = LoggingService(_state_store=build_default_state_store(args.state_file))

    try:
        if args.command == "status":
            print("ready")
            return 0

        if args.command == "list-adapters":
            print(json.dumps(service.list_available_adapters(), indent=2))
            return 0

        if args.command == "evidence":
            print(json.dumps(service.collect_operational_evidence(), indent=2, sort_keys=True))
            return 0

        if args.command == "query":
            rows = service.query_projection(
                filters=parse_json_object(args.filters_json),
                page=args.page,
                page_size=args.page_size,
            )
            print(json.dumps(rows, indent=2, sort_keys=True))
            return 0

        if args.command == "emit":
            record_id = service.log(
                level=args.level,
                message=args.message,
                attributes=parse_json_object(args.attributes_json),
                context=parse_json_object(args.context_json),
            )
            print(json.dumps({"record_id": record_id}, indent=2, sort_keys=True))
            return 0

        if args.command in {"log-debug", "log-info", "log-warn", "log-error", "log-fatal", "log-trace"}:
            attributes = parse_json_object(args.attributes_json)
            context = parse_json_object(args.context_json)
            level_map = {
                "log-debug": service.log_debug,
                "log-info": service.log_info,
                "log-warn": service.log_warn,
                "log-error": service.log_error,
                "log-fatal": service.log_fatal,
                "log-trace": service.log_trace,
            }
            record_id = level_map[args.command](message=args.message, attributes=attributes, context=context)
            print(json.dumps({"record_id": record_id}, indent=2, sort_keys=True))
            return 0

        if args.command == "bind-adapter":
            service.bind_adapter(args.adapter_key)
            print(json.dumps({"active_adapter_key": args.adapter_key}, indent=2, sort_keys=True))
            return 0

        if args.command == "bind-container-assignment":
            status = service.bind_container_assignment(
                container_binding_id=args.container_binding_id,
                container_backend_profile_id=args.container_backend_profile_id,
                container_lease_id=args.container_lease_id,
            )
            print(json.dumps(status, indent=2, sort_keys=True))
            return 0

        if args.command == "bind-execution-assignment":
            status = service.bind_execution_assignment(
                execution_binding_id=args.execution_binding_id,
                required_execution_profile_id=args.required_execution_profile_id,
                execution_lease_id=args.execution_lease_id,
                queue_policy_id=args.queue_policy_id,
                thread_safety_mode=args.thread_safety_mode,
            )
            print(json.dumps(status, indent=2, sort_keys=True))
            return 0

        if args.command == "unbind-container-assignment":
            service.unbind_container_assignment()
            print(json.dumps({"status": "unbound"}, indent=2, sort_keys=True))
            return 0

        if args.command == "unbind-execution-assignment":
            service.unbind_execution_assignment()
            print(json.dumps({"status": "unbound"}, indent=2, sort_keys=True))
            return 0

        if args.command == "container-assignment-status":
            print(json.dumps(service.get_container_assignment_status(), indent=2, sort_keys=True))
            return 0

        if args.command == "execution-assignment-status":
            print(json.dumps(service.get_execution_assignment_status(), indent=2, sort_keys=True))
            return 0

        if args.command == "dispatch":
            service.dispatch_round(args.round_id)
            print(json.dumps({"dispatched_round_id": args.round_id}, indent=2, sort_keys=True))
            return 0

        if args.command == "safepoint":
            service.enforce_safepoint(args.safepoint_id)
            print(json.dumps({"safepoint_id": args.safepoint_id}, indent=2, sort_keys=True))
            return 0

        if args.command == "schema-list":
            schema_ids = service.list_schema_ids()
            if args.as_json:
                rows = {schema_id: service.get_schema(schema_id) for schema_id in schema_ids}
                print(json.dumps(rows, indent=2, sort_keys=True))
            else:
                print(json.dumps(schema_ids, indent=2, sort_keys=True))
            return 0

        if args.command == "schema-get":
            row = service.get_schema(args.schema_id)
            print(json.dumps(row, indent=2, sort_keys=True))
            return 0

        if args.command == "schema-create":
            schema_payload = parse_json_object(args.schema_json)
            service.create_schema(args.schema_id, schema_payload)
            print(json.dumps({"schema_id": args.schema_id, "status": "created"}, indent=2, sort_keys=True))
            return 0

        if args.command == "schema-update":
            schema_payload = parse_json_object(args.schema_json)
            service.update_schema(args.schema_id, schema_payload)
            print(json.dumps({"schema_id": args.schema_id, "status": "updated"}, indent=2, sort_keys=True))
            return 0

        if args.command == "schema-delete":
            service.delete_schema(args.schema_id)
            print(json.dumps({"schema_id": args.schema_id, "status": "deleted"}, indent=2, sort_keys=True))
            return 0

        if args.command == "policy-list":
            policy_ids = service.list_policy_ids()
            if args.as_json:
                rows = {policy_id: service.get_policy(policy_id) for policy_id in policy_ids}
                print(json.dumps(rows, indent=2, sort_keys=True))
            else:
                print(json.dumps(policy_ids, indent=2, sort_keys=True))
            return 0

        if args.command == "policy-get":
            row = service.get_policy(args.policy_id)
            print(json.dumps(row, indent=2, sort_keys=True))
            return 0

        if args.command == "policy-create":
            policy_payload = parse_json_object(args.policy_json)
            service.create_policy(args.policy_id, policy_payload)
            print(json.dumps({"policy_id": args.policy_id, "status": "created"}, indent=2, sort_keys=True))
            return 0

        if args.command == "policy-update":
            policy_payload = parse_json_object(args.policy_json)
            service.update_policy(args.policy_id, policy_payload)
            print(json.dumps({"policy_id": args.policy_id, "status": "updated"}, indent=2, sort_keys=True))
            return 0

        if args.command == "policy-delete":
            service.delete_policy(args.policy_id)
            print(json.dumps({"policy_id": args.policy_id, "status": "deleted"}, indent=2, sort_keys=True))
            return 0

        if args.command == "profile-list":
            profile_ids = service.list_runtime_profile_ids()
            if args.as_json:
                rows = {profile_id: service.get_runtime_profile(profile_id) for profile_id in profile_ids}
                print(json.dumps(rows, indent=2, sort_keys=True))
            else:
                print(json.dumps(profile_ids, indent=2, sort_keys=True))
            return 0

        if args.command == "profile-get":
            row = service.get_runtime_profile(args.profile_id)
            print(json.dumps(row, indent=2, sort_keys=True))
            return 0

        if args.command == "profile-create":
            profile_payload = parse_json_object(args.profile_json)
            service.create_runtime_profile(args.profile_id, profile_payload)
            print(json.dumps({"profile_id": args.profile_id, "status": "created"}, indent=2, sort_keys=True))
            return 0

        if args.command == "profile-update":
            profile_payload = parse_json_object(args.profile_json)
            service.update_runtime_profile(args.profile_id, profile_payload)
            print(json.dumps({"profile_id": args.profile_id, "status": "updated"}, indent=2, sort_keys=True))
            return 0

        if args.command == "profile-delete":
            service.delete_runtime_profile(args.profile_id)
            print(json.dumps({"profile_id": args.profile_id, "status": "deleted"}, indent=2, sort_keys=True))
            return 0

        if args.command == "production-profile-list":
            profile_ids = service.list_production_profile_ids()
            if args.as_json:
                rows = {profile_id: service.get_production_profile(profile_id) for profile_id in profile_ids}
                print(json.dumps(rows, indent=2, sort_keys=True))
            else:
                print(json.dumps(profile_ids, indent=2, sort_keys=True))
            return 0

        if args.command == "production-profile-get":
            row = service.get_production_profile(args.profile_id)
            print(json.dumps(row, indent=2, sort_keys=True))
            return 0

        if args.command == "production-profile-create":
            profile_payload = parse_json_object(args.profile_json)
            service.create_production_profile(args.profile_id, profile_payload)
            print(json.dumps({"profile_id": args.profile_id, "status": "created"}, indent=2, sort_keys=True))
            return 0

        if args.command == "production-profile-update":
            profile_payload = parse_json_object(args.profile_json)
            service.update_production_profile(args.profile_id, profile_payload)
            print(json.dumps({"profile_id": args.profile_id, "status": "updated"}, indent=2, sort_keys=True))
            return 0

        if args.command == "production-profile-delete":
            service.delete_production_profile(args.profile_id)
            print(json.dumps({"profile_id": args.profile_id, "status": "deleted"}, indent=2, sort_keys=True))
            return 0

        if args.command == "production-profile-activate":
            activation = service.activate_production_profile(args.profile_id)
            print(json.dumps(activation, indent=2, sort_keys=True))
            return 0


        if args.command == "config-list":
            config_ids = service.list_configuration_ids(args.config_type)
            if args.as_json:
                rows = {
                    config_id: service.get_configuration(args.config_type, config_id)
                    for config_id in config_ids
                }
                print(json.dumps(rows, indent=2, sort_keys=True))
            else:
                print(json.dumps(config_ids, indent=2, sort_keys=True))
            return 0

        if args.command == "config-get":
            row = service.get_configuration(args.config_type, args.config_id)
            print(json.dumps(row, indent=2, sort_keys=True))
            return 0

        if args.command == "config-create":
            config_payload = parse_json_object(args.config_json)
            service.create_configuration(args.config_type, args.config_id, config_payload)
            print(
                json.dumps(
                    {
                        "config_type": args.config_type,
                        "config_id": args.config_id,
                        "status": "created",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "config-update":
            config_payload = parse_json_object(args.config_json)
            service.update_configuration(args.config_type, args.config_id, config_payload)
            print(
                json.dumps(
                    {
                        "config_type": args.config_type,
                        "config_id": args.config_id,
                        "status": "updated",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "config-delete":
            service.delete_configuration(args.config_type, args.config_id)
            print(
                json.dumps(
                    {
                        "config_type": args.config_type,
                        "config_id": args.config_id,
                        "status": "deleted",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "config-apply":
            result = service.apply_configuration(args.config_type, args.config_id)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "set-dispatch-failure-policy":
            service.configure_dispatch_failure_policy(parse_json_object(args.policy_json))
            print(json.dumps({"policy_id": "dispatch.failure_policy", "status": "configured"}, indent=2, sort_keys=True))
            return 0

        if args.command == "set-signal-qos-profile":
            service.configure_signal_qos_profile(parse_json_object(args.policy_json))
            print(json.dumps({"policy_id": "signal.qos_profile", "status": "configured"}, indent=2, sort_keys=True))
            return 0

        if args.command == "set-mandatory-label-schema":
            service.configure_mandatory_label_schema(parse_json_object(args.policy_json))
            print(
                json.dumps({"policy_id": "signal.mandatory_label_schema", "status": "configured"}, indent=2, sort_keys=True)
            )
            return 0

        if args.command == "set-slot-lifecycle-policy":
            service.configure_slot_lifecycle_policy(parse_json_object(args.policy_json))
            print(json.dumps({"policy_id": "slot.lifecycle_policy", "status": "configured"}, indent=2, sort_keys=True))
            return 0

        if args.command == "set-level-container-policy":
            service.configure_level_container_policy(parse_json_object(args.policy_json))
            print(json.dumps({"policy_id": "container.level_policy", "status": "configured"}, indent=2, sort_keys=True))
            return 0

        if args.command == "set-resolver-pipeline-policy":
            service.configure_resolver_pipeline_policy(parse_json_object(args.policy_json))
            print(
                json.dumps({"policy_id": "resolver.pipeline_policy", "status": "configured"}, indent=2, sort_keys=True)
            )
            return 0

        if args.command == "set-previewer-profile":
            service.configure_previewer_profile(parse_json_object(args.profile_json))
            print(json.dumps({"profile_id": "previewer.profile", "status": "configured"}, indent=2, sort_keys=True))
            return 0

        if args.command == "set-loglevel-api-policy":
            service.configure_loglevel_api_policy(parse_json_object(args.policy_json))
            print(json.dumps({"policy_id": "api.log_level_policy", "status": "configured"}, indent=2, sort_keys=True))
            return 0

        if args.command == "preview-console":
            rendered = service.preview_console(mode=args.mode, limit=args.limit)
            print(rendered)
            return 0

        if args.command == "preview-web":
            payload = service.preview_web(mode=args.mode, limit=args.limit)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(run_cli())
