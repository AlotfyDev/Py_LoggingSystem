from __future__ import annotations

from typing import Any


def build_default_provider_entries() -> list[dict[str, Any]]:
    return [
        {
            "provider_id": "provider.local.inmemory.level_containers",
            "backend_type": "local_memory",
            "scope_support": ["in_process"],
            "ordering_guarantee": "strict_per_partition",
            "ack_model": "inprocess_commit",
            "durability_level": "volatile_memory",
            "qos_support": ["at_most_once", "bounded_queue"],
            "lease_required": True,
            "execution_plane_relation": "orthogonal_explicit_binding",
            "required_execution_profile_id": "exec.logging.local.default",
            "backend_execution_scope": "provider_backend",
            "supported_partition_modes": ["by_level", "by_tenant", "hybrid"],
            "connection_profile_id": "connector.local.memory",
            "persistence_profile_id": "persistence.local.volatile",
            "fail_closed_conditions": [
                "missing_container_lease",
                "unsupported_partition_mode",
            ],
        },
        {
            "provider_id": "provider.redis.streams",
            "backend_type": "redis_streams",
            "scope_support": ["inter_process", "distributed"],
            "ordering_guarantee": "stream_order_per_key",
            "ack_model": "consumer_group_ack",
            "durability_level": "redis_aof_or_rdb_profile_required",
            "qos_support": ["at_least_once", "retry_with_backpressure"],
            "lease_required": True,
            "execution_plane_relation": "orthogonal_explicit_binding",
            "required_execution_profile_id": "exec.logging.distributed.redis",
            "backend_execution_scope": "provider_backend",
            "supported_partition_modes": ["by_level", "by_tenant", "hybrid"],
            "connection_profile_id": "connector.redis.tcp_tls",
            "persistence_profile_id": "persistence.redis.aof",
            "fail_closed_conditions": [
                "missing_redis_connector_binding",
                "missing_persistence_profile",
                "unsupported_ack_mode",
            ],
        },
    ]


def build_default_connection_entries() -> list[dict[str, Any]]:
    return [
        {
            "connector_profile_id": "connector.local.memory",
            "provider_id": "provider.local.inmemory.level_containers",
            "connector_type": "local",
            "protocol": "inprocess_api",
            "auth_modes": ["none"],
            "tls_modes": ["not_applicable"],
            "retry_policy": {"mode": "none", "max_attempts": 0},
            "circuit_breaker_policy": {"enabled": False},
            "session_or_lease_requirements": {
                "lease_required": True,
                "session_required": False,
            },
            "execution_plane_relation": "orthogonal_explicit_binding",
            "backend_execution_scope": "connector_backend",
            "capabilities": ["low_latency", "direct_inprocess_calls"],
            "fail_closed_conditions": ["lease_required_but_missing"],
        },
        {
            "connector_profile_id": "connector.redis.tcp_tls",
            "provider_id": "provider.redis.streams",
            "connector_type": "redis",
            "protocol": "redis_tcp",
            "auth_modes": ["password", "acl"],
            "tls_modes": ["tls_optional", "tls_required"],
            "retry_policy": {"mode": "exponential_backoff", "max_attempts": 8},
            "circuit_breaker_policy": {
                "enabled": True,
                "failure_threshold": 5,
                "reset_timeout_seconds": 30,
            },
            "session_or_lease_requirements": {
                "lease_required": True,
                "session_required": True,
                "session_ttl_seconds": 3600,
            },
            "execution_plane_relation": "orthogonal_explicit_binding",
            "backend_execution_scope": "connector_backend",
            "capabilities": [
                "distributed_connectivity",
                "reconnect_support",
                "command_timeout_control",
            ],
            "fail_closed_conditions": [
                "tls_required_but_not_configured",
                "auth_required_but_missing_credentials",
                "retry_policy_missing_for_distributed_connector",
            ],
        },
    ]


def build_default_persistence_entries() -> list[dict[str, Any]]:
    return [
        {
            "persistence_profile_id": "persistence.local.volatile",
            "provider_id": "provider.local.inmemory.level_containers",
            "durability_level": "volatile_memory",
            "replay_capability": "none",
            "retention_capability": {
                "mode": "bounded_queue",
                "max_records_required": True,
                "max_age_seconds_optional": True,
            },
            "compaction_capability": {"supported": False},
            "consistency_model": "inprocess_single_writer",
            "ack_semantics": "inprocess_commit",
            "execution_plane_relation": "orthogonal_explicit_binding",
            "backend_execution_scope": "persistence_backend",
            "backup_restore_support": {
                "snapshot_export": "optional",
                "restore": "optional",
            },
            "eviction_policy_compatibility": ["drop_oldest", "size_bound_enforced"],
            "fail_closed_conditions": [
                "persistence_profile_requires_durability_but_is_volatile",
            ],
        },
        {
            "persistence_profile_id": "persistence.redis.aof",
            "provider_id": "provider.redis.streams",
            "durability_level": "durable_append_only",
            "replay_capability": "stream_replay_with_offsets",
            "retention_capability": {
                "mode": "stream_trim_policy",
                "max_len_required": True,
                "max_age_seconds_optional": True,
            },
            "compaction_capability": {"supported": True, "strategy": "stream_trim"},
            "consistency_model": "distributed_eventual_with_ack",
            "ack_semantics": "consumer_group_ack",
            "execution_plane_relation": "orthogonal_explicit_binding",
            "backend_execution_scope": "persistence_backend",
            "backup_restore_support": {
                "snapshot_export": "supported",
                "restore": "supported",
            },
            "eviction_policy_compatibility": ["trim_by_length", "trim_by_age"],
            "fail_closed_conditions": [
                "ack_model_mismatch_with_provider",
                "durability_required_but_aof_disabled",
            ],
        },
    ]
