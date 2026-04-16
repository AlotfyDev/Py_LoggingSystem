from __future__ import annotations

import argparse


def _add_log_payload_args(cmd: argparse.ArgumentParser) -> None:
    cmd.add_argument("--message", required=True)
    cmd.add_argument("--attributes-json", default="{}")
    cmd.add_argument("--context-json", default="{}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LoggingService CLI")
    parser.add_argument(
        "--state-file",
        default=None,
        help="Optional path to persistent state JSON file.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Print subsystem readiness")
    sub.add_parser("list-adapters", help="List adapter keys")
    sub.add_parser("evidence", help="Print operational evidence")

    query_cmd = sub.add_parser("query", help="Query subsystem state")
    query_cmd.add_argument("--filters-json", default="{}")
    query_cmd.add_argument("--page", type=int, default=1)
    query_cmd.add_argument("--page-size", type=int, default=100)

    emit_cmd = sub.add_parser("emit", help="Submit a log payload")
    emit_cmd.add_argument("--level", required=True)
    _add_log_payload_args(emit_cmd)

    log_debug_cmd = sub.add_parser("log-debug", help="Submit DEBUG level log")
    _add_log_payload_args(log_debug_cmd)
    log_info_cmd = sub.add_parser("log-info", help="Submit INFO level log")
    _add_log_payload_args(log_info_cmd)
    log_warn_cmd = sub.add_parser("log-warn", help="Submit WARN level log")
    _add_log_payload_args(log_warn_cmd)
    log_error_cmd = sub.add_parser("log-error", help="Submit ERROR level log")
    _add_log_payload_args(log_error_cmd)
    log_fatal_cmd = sub.add_parser("log-fatal", help="Submit FATAL level log")
    _add_log_payload_args(log_fatal_cmd)
    log_trace_cmd = sub.add_parser("log-trace", help="Submit TRACE level log")
    _add_log_payload_args(log_trace_cmd)

    bind_cmd = sub.add_parser("bind-adapter", help="Bind active adapter")
    bind_cmd.add_argument("--adapter-key", required=True)

    bind_container_cmd = sub.add_parser("bind-container-assignment", help="Bind container backend assignment")
    bind_container_cmd.add_argument("--container-binding-id", required=True)
    bind_container_cmd.add_argument("--container-backend-profile-id", required=True)
    bind_container_cmd.add_argument("--container-lease-id", default=None)

    bind_execution_cmd = sub.add_parser("bind-execution-assignment", help="Bind execution/thread assignment")
    bind_execution_cmd.add_argument("--execution-binding-id", required=True)
    bind_execution_cmd.add_argument("--required-execution-profile-id", required=True)
    bind_execution_cmd.add_argument("--execution-lease-id", default=None)
    bind_execution_cmd.add_argument("--queue-policy-id", default=None)
    bind_execution_cmd.add_argument("--thread-safety-mode", default=None)

    sub.add_parser("unbind-container-assignment", help="Release current container backend assignment")
    sub.add_parser("unbind-execution-assignment", help="Release current execution/thread assignment")
    sub.add_parser("container-assignment-status", help="Get current container assignment status")
    sub.add_parser("execution-assignment-status", help="Get current execution assignment status")

    dispatch_cmd = sub.add_parser("dispatch", help="Dispatch pending round")
    dispatch_cmd.add_argument("--round-id", required=True)

    safepoint_cmd = sub.add_parser("safepoint", help="Enforce safepoint")
    safepoint_cmd.add_argument("--safepoint-id", required=True)

    schema_list = sub.add_parser("schema-list", help="List schema catalog ids")
    schema_list.add_argument("--as-json", action="store_true", help="Output full schema objects instead of ids")

    schema_get = sub.add_parser("schema-get", help="Get one schema catalog entry")
    schema_get.add_argument("--schema-id", required=True)

    schema_create = sub.add_parser("schema-create", help="Create schema catalog entry")
    schema_create.add_argument("--schema-id", required=True)
    schema_create.add_argument("--schema-json", required=True)

    schema_update = sub.add_parser("schema-update", help="Update schema catalog entry")
    schema_update.add_argument("--schema-id", required=True)
    schema_update.add_argument("--schema-json", required=True)

    schema_delete = sub.add_parser("schema-delete", help="Delete schema catalog entry")
    schema_delete.add_argument("--schema-id", required=True)

    policy_list = sub.add_parser("policy-list", help="List policy ids")
    policy_list.add_argument("--as-json", action="store_true", help="Output full policy objects instead of ids")

    policy_get = sub.add_parser("policy-get", help="Get one policy entry")
    policy_get.add_argument("--policy-id", required=True)

    policy_create = sub.add_parser("policy-create", help="Create policy entry")
    policy_create.add_argument("--policy-id", required=True)
    policy_create.add_argument("--policy-json", required=True)

    policy_update = sub.add_parser("policy-update", help="Update policy entry")
    policy_update.add_argument("--policy-id", required=True)
    policy_update.add_argument("--policy-json", required=True)

    policy_delete = sub.add_parser("policy-delete", help="Delete policy entry")
    policy_delete.add_argument("--policy-id", required=True)

    profile_list = sub.add_parser("profile-list", help="List runtime profile ids")
    profile_list.add_argument("--as-json", action="store_true", help="Output full runtime profile objects instead of ids")

    profile_get = sub.add_parser("profile-get", help="Get one runtime profile entry")
    profile_get.add_argument("--profile-id", required=True)

    profile_create = sub.add_parser("profile-create", help="Create runtime profile entry")
    profile_create.add_argument("--profile-id", required=True)
    profile_create.add_argument("--profile-json", required=True)

    profile_update = sub.add_parser("profile-update", help="Update runtime profile entry")
    profile_update.add_argument("--profile-id", required=True)
    profile_update.add_argument("--profile-json", required=True)

    profile_delete = sub.add_parser("profile-delete", help="Delete runtime profile entry")
    profile_delete.add_argument("--profile-id", required=True)

    prod_profile_list = sub.add_parser("production-profile-list", help="List production profile ids")
    prod_profile_list.add_argument("--as-json", action="store_true", help="Output full production profile objects instead of ids")

    prod_profile_get = sub.add_parser("production-profile-get", help="Get one production profile entry")
    prod_profile_get.add_argument("--profile-id", required=True)

    prod_profile_create = sub.add_parser("production-profile-create", help="Create production profile entry")
    prod_profile_create.add_argument("--profile-id", required=True)
    prod_profile_create.add_argument("--profile-json", required=True)

    prod_profile_update = sub.add_parser("production-profile-update", help="Update production profile entry")
    prod_profile_update.add_argument("--profile-id", required=True)
    prod_profile_update.add_argument("--profile-json", required=True)

    prod_profile_delete = sub.add_parser("production-profile-delete", help="Delete production profile entry")
    prod_profile_delete.add_argument("--profile-id", required=True)

    prod_profile_activate = sub.add_parser("production-profile-activate", help="Activate production profile and bind runtime resources")
    prod_profile_activate.add_argument("--profile-id", required=True)

    dispatch_failure = sub.add_parser("set-dispatch-failure-policy", help="Configure dispatch failure policy")
    dispatch_failure.add_argument("--policy-json", required=True)

    qos_profile = sub.add_parser("set-signal-qos-profile", help="Configure signal QoS policy")
    qos_profile.add_argument("--policy-json", required=True)

    label_schema = sub.add_parser("set-mandatory-label-schema", help="Configure mandatory label schema")
    label_schema.add_argument("--policy-json", required=True)

    slot_lifecycle = sub.add_parser("set-slot-lifecycle-policy", help="Configure slot lifecycle policy")
    slot_lifecycle.add_argument("--policy-json", required=True)

    level_container = sub.add_parser("set-level-container-policy", help="Configure level container policy")
    level_container.add_argument("--policy-json", required=True)

    resolver_pipeline = sub.add_parser("set-resolver-pipeline-policy", help="Configure resolver pipeline policy")
    resolver_pipeline.add_argument("--policy-json", required=True)

    previewer_profile = sub.add_parser("set-previewer-profile", help="Configure previewer profile")
    previewer_profile.add_argument("--profile-json", required=True)

    level_api_policy = sub.add_parser("set-loglevel-api-policy", help="Configure dedicated level API policy")
    level_api_policy.add_argument("--policy-json", required=True)

    preview_console = sub.add_parser("preview-console", help="Render console preview from stored records")
    preview_console.add_argument("--mode", default=None, choices=["pop_single", "collective", "system_pause"])
    preview_console.add_argument("--limit", type=int, default=50)

    preview_web = sub.add_parser("preview-web", help="Render web preview payload from stored records")
    preview_web.add_argument("--mode", default=None, choices=["pop_single", "collective", "system_pause"])
    preview_web.add_argument("--limit", type=int, default=50)


    config_types = [
        "schema",
        "policy",
        "retention",
        "previewer_profile",
        "adapter_binding",
        "container_binding",
        "execution_binding",
        "provider_catalog_entry",
        "connection_catalog_entry",
        "persistence_catalog_entry",
        "production_profile",
    ]

    config_list = sub.add_parser("config-list", help="List typed configuration ids by config type")
    config_list.add_argument("--config-type", required=True, choices=config_types)
    config_list.add_argument("--as-json", action="store_true", help="Output full config objects instead of ids")

    config_get = sub.add_parser("config-get", help="Get one typed configuration entry")
    config_get.add_argument("--config-type", required=True, choices=config_types)
    config_get.add_argument("--config-id", required=True)

    config_create = sub.add_parser("config-create", help="Create typed configuration entry")
    config_create.add_argument("--config-type", required=True, choices=config_types)
    config_create.add_argument("--config-id", required=True)
    config_create.add_argument("--config-json", required=True)

    config_update = sub.add_parser("config-update", help="Update typed configuration entry")
    config_update.add_argument("--config-type", required=True, choices=config_types)
    config_update.add_argument("--config-id", required=True)
    config_update.add_argument("--config-json", required=True)

    config_delete = sub.add_parser("config-delete", help="Delete typed configuration entry")
    config_delete.add_argument("--config-type", required=True, choices=config_types)
    config_delete.add_argument("--config-id", required=True)

    config_apply = sub.add_parser("config-apply", help="Apply typed configuration by config type and id")
    config_apply.add_argument("--config-type", required=True, choices=config_types)
    config_apply.add_argument("--config-id", required=True)

    return parser
