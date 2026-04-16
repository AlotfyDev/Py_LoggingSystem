from __future__ import annotations

import unittest

from logging_system.services.logging_service import LoggingService
from logging_system.tests.support import InMemoryStateStore


class ProviderCatalogsBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = LoggingService(_state_store=InMemoryStateStore())

    def test_default_provider_catalog_integrity_passes(self) -> None:
        report = self.service.validate_provider_catalog_integrity()
        self.assertTrue(report["pass_fail"])
        self.assertEqual(report["violations_count"], 0)
        self.assertGreaterEqual(report["counts"]["provider_entries"], 2)

    def test_provider_connection_persistence_catalog_crud_roundtrip(self) -> None:
        provider_id = "provider.local.test"
        connector_profile_id = "connector.local.test"
        persistence_profile_id = "persistence.local.test"

        self.service.create_connection_catalog_entry(
            connector_profile_id,
            {
                "provider_id": provider_id,
                "connector_type": "local",
                "protocol": "inprocess_api",
                "auth_modes": ["none"],
                "tls_modes": ["not_applicable"],
                "retry_policy": {"mode": "none", "max_attempts": 0},
                "circuit_breaker_policy": {"enabled": False},
                "session_or_lease_requirements": {"lease_required": True, "session_required": False},
                "execution_plane_relation": "orthogonal_explicit_binding",
                "backend_execution_scope": "connector_backend",
                "capabilities": ["low_latency"],
                "fail_closed_conditions": ["lease_required_but_missing"],
            },
        )
        self.service.create_persistence_catalog_entry(
            persistence_profile_id,
            {
                "provider_id": provider_id,
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
                "backup_restore_support": {"snapshot_export": "optional", "restore": "optional"},
                "eviction_policy_compatibility": ["drop_oldest"],
                "fail_closed_conditions": ["durability_required_but_volatile"],
            },
        )
        self.service.create_provider_catalog_entry(
            provider_id,
            {
                "backend_type": "local_memory",
                "scope_support": ["in_process"],
                "ordering_guarantee": "strict_per_partition",
                "ack_model": "inprocess_commit",
                "durability_level": "volatile_memory",
                "qos_support": ["at_most_once"],
                "lease_required": True,
                "execution_plane_relation": "orthogonal_explicit_binding",
                "required_execution_profile_id": "exec.logging.local.default",
                "backend_execution_scope": "provider_backend",
                "supported_partition_modes": ["by_level"],
                "connection_profile_id": connector_profile_id,
                "persistence_profile_id": persistence_profile_id,
                "fail_closed_conditions": ["missing_container_lease"],
            },
        )

        self.assertIn(provider_id, self.service.list_provider_catalog_entries())
        self.assertIn(connector_profile_id, self.service.list_connection_catalog_entries())
        self.assertIn(persistence_profile_id, self.service.list_persistence_catalog_entries())

        provider_row = self.service.get_provider_catalog_entry(provider_id)
        self.assertEqual(provider_row["provider_id"], provider_id)
        self.assertEqual(provider_row["connection_profile_id"], connector_profile_id)

        report = self.service.validate_provider_catalog_integrity()
        self.assertTrue(report["pass_fail"])
        self.assertEqual(report["violations_count"], 0)

        self.service.delete_provider_catalog_entry(provider_id)
        self.assertNotIn(provider_id, self.service.list_provider_catalog_entries())

    def test_provider_update_rejected_when_ack_mismatch(self) -> None:
        provider_id = "provider.local.inmemory.level_containers"
        original = self.service.get_provider_catalog_entry(provider_id)

        with self.assertRaises(ValueError):
            self.service.update_provider_catalog_entry(
                provider_id,
                {
                    "backend_type": original["backend_type"],
                    "scope_support": original["scope_support"],
                    "ordering_guarantee": original["ordering_guarantee"],
                    "ack_model": "wrong_ack_model",
                    "durability_level": original["durability_level"],
                    "qos_support": original["qos_support"],
                    "lease_required": original["lease_required"],
                    "execution_plane_relation": original["execution_plane_relation"],
                    "required_execution_profile_id": original["required_execution_profile_id"],
                    "backend_execution_scope": original["backend_execution_scope"],
                    "supported_partition_modes": original["supported_partition_modes"],
                    "connection_profile_id": original["connection_profile_id"],
                    "persistence_profile_id": original["persistence_profile_id"],
                    "fail_closed_conditions": original["fail_closed_conditions"],
                },
            )

        restored = self.service.get_provider_catalog_entry(provider_id)
        self.assertEqual(restored["ack_model"], original["ack_model"])


if __name__ == "__main__":
    unittest.main()
